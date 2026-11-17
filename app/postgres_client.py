"""PostgreSQL data access for Outreach.

This module is intentionally independent of the HTTP database API. All SQL
identifiers are quoted and values are bound as parameters.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def database_url() -> str:
    value = (os.getenv('OUTREACH_DATABASE_URL') or os.getenv('DATABASE_URL') or '').strip()
    if not value:
        raise RuntimeError('Missing OUTREACH_DATABASE_URL or DATABASE_URL')
    return value


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _identifier(name):
    parts = name.split('.')
    if not all(part and part.replace('_', '').isalnum() for part in parts):
        raise ValueError('Invalid database identifier')
    return sql.Identifier(*parts)


def _split_projection(value):
    parts, start, depth = [], 0, 0
    for index, char in enumerate(value):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    if depth or any(not part for part in parts):
        raise ValueError('Invalid projection')
    return parts


class Response:
    def __init__(self, data=None, count=None):
        self.data = _json_value(data)
        self.count = count


class Client:
    def __init__(self, url=None):
        self.url = url or database_url()

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, params):
        return RpcQuery(self, name, params)

    def connect(self):
        return psycopg.connect(self.url, row_factory=dict_row, connect_timeout=15)


def create_client(*_args, **_kwargs):
    return Client()


class Query:
    def __init__(self, client, table):
        self.client, self.table_name = client, table
        self.operation, self.fields, self.payload = 'select', '*', None
        self.filters, self.sort = [], []
        self.limit_value, self.offset, self.head, self.want_count = None, 0, False, False
        self.conflict = None

    def select(self, fields='*', *, count=None, head=False):
        self.fields, self.head, self.want_count = fields, head, count == 'exact'
        return self

    def insert(self, payload):
        self.operation, self.payload = 'insert', payload
        return self

    def update(self, payload):
        self.operation, self.payload = 'update', payload
        return self

    def upsert(self, payload, *, on_conflict=None):
        self.operation, self.payload, self.conflict = 'upsert', payload, on_conflict
        return self

    def delete(self):
        self.operation = 'delete'
        return self

    def _filter(self, field, operator, value):
        self.filters.append((field, operator, value))
        return self

    def eq(self, field, value): return self._filter(field, '=', value)
    def neq(self, field, value): return self._filter(field, '<>', value)
    def gte(self, field, value): return self._filter(field, '>=', value)
    def lte(self, field, value): return self._filter(field, '<=', value)
    def lt(self, field, value): return self._filter(field, '<', value)
    def gt(self, field, value): return self._filter(field, '>', value)
    def like(self, field, value): return self._filter(field, 'LIKE', value)
    def in_(self, field, values): return self._filter(field, 'IN', list(values))

    def order(self, field, *, desc=False, **_kwargs):
        self.sort.append((field, desc))
        return self

    def limit(self, value):
        self.limit_value = int(value)
        return self

    def range(self, start, end):
        self.offset, self.limit_value = int(start), int(end) - int(start) + 1
        return self

    def _where(self):
        expressions, values = [], []
        for name, operator, value in self.filters:
            field = _identifier(name if '.' in name else 'base.' + name)
            if operator == 'IN':
                if not value:
                    expressions.append(sql.SQL('FALSE'))
                    continue
                expressions.append(sql.SQL('{} IN ({})').format(field, sql.SQL(',').join(sql.Placeholder() for _ in value)))
                values.extend(value)
            elif value is None and operator in ('=', '<>'):
                expressions.append(sql.SQL('{} IS {}NULL').format(field, sql.SQL('NOT ') if operator == '<>' else sql.SQL('')))
            else:
                expressions.append(sql.SQL('{} {} %s').format(field, sql.SQL(operator)))
                values.append(value)
        return (sql.SQL(' WHERE ') + sql.SQL(' AND ').join(expressions) if expressions else sql.SQL('')), values

    def _selection(self):
        fields, joins = [], []
        relations = {
            ('outreach_job_targets', 'outreach_prospects'): ('prospect_id', 'id'),
            ('outreach_ready_notifications', 'outreach_message_batches'): ('batch_id', 'id'),
        }
        for item in _split_projection(self.fields):
            if item == '*':
                fields.append(sql.SQL('base.*'))
            elif '(' not in item:
                fields.append(_identifier('base.' + item))
            else:
                relation, nested = item.split('(', 1)
                inner = relation.endswith('!inner')
                relation = relation.removesuffix('!inner')
                keys = relations.get((self.table_name, relation))
                if not keys:
                    raise ValueError('Unsupported database relationship')
                nested = nested[:-1]
                if nested == '*':
                    expression = sql.SQL('to_jsonb({})').format(_identifier(relation))
                else:
                    pairs = []
                    for column in _split_projection(nested):
                        pairs.extend((sql.Literal(column), _identifier(relation + '.' + column)))
                    expression = sql.SQL('jsonb_build_object({})').format(sql.SQL(', ').join(pairs))
                fields.append(sql.SQL('CASE WHEN {} IS NULL THEN NULL ELSE {} END AS {}').format(
                    _identifier(relation + '.' + keys[1]), expression, _identifier(relation)))
                joins.append(sql.SQL('{} JOIN {} AS {} ON {} = {}').format(
                    sql.SQL('INNER') if inner else sql.SQL('LEFT'), _identifier('public.' + relation),
                    _identifier(relation), _identifier('base.' + keys[0]), _identifier(relation + '.' + keys[1])))
        return sql.SQL(', ').join(fields), sql.SQL(' ').join(joins)

    @staticmethod
    def _value(key, value):
        if key == 'conversation_messages' and value is not None:
            return Jsonb(value)
        return value

    def execute(self):
        where, params = self._where()
        table = _identifier('public.' + self.table_name)
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                if self.operation == 'select':
                    selection, joins = self._selection()
                    if self.head:
                        selection = sql.SQL('count(*) AS count')
                    query = sql.SQL('SELECT {} FROM {} AS base {}').format(selection, table, joins) + where
                    if not self.head and self.sort:
                        query += sql.SQL(' ORDER BY ') + sql.SQL(', ').join(
                            sql.SQL('{} {}').format(_identifier(field if '.' in field else 'base.' + field), sql.SQL('DESC') if desc else sql.SQL('ASC'))
                            for field, desc in self.sort)
                    if not self.head and self.limit_value is not None:
                        query += sql.SQL(' LIMIT %s OFFSET %s')
                        params += [self.limit_value, self.offset]
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return Response([] if self.head else rows, rows[0]['count'] if self.head and rows else None)
                if self.operation in ('insert', 'upsert'):
                    rows = self.payload if isinstance(self.payload, list) else [self.payload]
                    if not rows:
                        return Response([])
                    keys = list(rows[0])
                    if any(set(row) != set(keys) for row in rows):
                        raise ValueError('All inserted rows must have the same columns')
                    query = sql.SQL('INSERT INTO {} ({}) VALUES {}').format(table,
                        sql.SQL(', ').join(_identifier(k) for k in keys),
                        sql.SQL(', ').join(sql.SQL('({})').format(sql.SQL(', ').join(sql.Placeholder() for _ in keys)) for _ in rows))
                    params = [self._value(k, row[k]) for row in rows for k in keys]
                    if self.operation == 'upsert':
                        conflict = (self.conflict or '').split(',')
                        if not all(conflict): raise ValueError('Upsert requires on_conflict')
                        updates = [k for k in keys if k not in conflict]
                        action = (sql.SQL('DO UPDATE SET ') + sql.SQL(', ').join(
                            sql.SQL('{} = EXCLUDED.{}').format(_identifier(k), _identifier(k)) for k in updates)
                            if updates else sql.SQL('DO NOTHING'))
                        query += sql.SQL(' ON CONFLICT ({}) ').format(sql.SQL(', ').join(_identifier(k) for k in conflict)) + action
                elif self.operation == 'update':
                    if not self.payload: raise ValueError('Empty update')
                    assignments = sql.SQL(', ').join(sql.SQL('{} = %s').format(_identifier(k)) for k in self.payload)
                    query = sql.SQL('UPDATE {} AS base SET {}').format(table, assignments) + where
                    params = [self._value(k, v) for k, v in self.payload.items()] + params
                elif self.operation == 'delete':
                    query = sql.SQL('DELETE FROM {} AS base').format(table) + where
                else:
                    raise ValueError('Unsupported operation')
                cur.execute(query + sql.SQL(' RETURNING *'), params)
                return Response(cur.fetchall())


class RpcQuery:
    def __init__(self, client, name, params):
        self.client, self.name, self.params = client, name, params

    def execute(self):
        args, values = [], []
        for key, value in self.params.items():
            cast = sql.SQL('::uuid[]') if key == 'p_batch_ids' else sql.SQL('')
            args.append(sql.SQL('{} => %s{}').format(_identifier(key), cast))
            values.append(Jsonb(value) if key == 'p_targets' else value)
        query = sql.SQL('SELECT {}({}) AS result').format(_identifier('public.' + self.name), sql.SQL(', ').join(args))
        with self.client.connect() as conn, conn.cursor() as cur:
            cur.execute(query, values)
            row = cur.fetchone()
            return Response(row['result'] if row else None)


class AsyncQuery:
    def __init__(self, query):
        self._query = query

    def __getattr__(self, name):
        if name == 'execute':
            async def execute():
                import asyncio
                return await asyncio.to_thread(self._query.execute)
            return execute
        def chain(*args, **kwargs):
            getattr(self._query, name)(*args, **kwargs)
            return self
        return chain


class AsyncClient:
    def __init__(self):
        self._client = Client()

    def table(self, name):
        return AsyncQuery(self._client.table(name))


async def acreate_client(*_args, **_kwargs):
    return AsyncClient()
