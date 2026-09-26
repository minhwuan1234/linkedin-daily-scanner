(() => {
  const trigger = document.getElementById("usageGuideButton");
  const dialog = document.getElementById("usageGuideDialog");
  const closeButton = document.getElementById("usageGuideCloseButton");
  const previousButton = document.getElementById("usageGuidePreviousButton");
  const nextButton = document.getElementById("usageGuideNextButton");
  const stepLabel = document.getElementById("usageGuideStepLabel");
  const title = document.getElementById("usageGuideTitle");
  const description = document.getElementById("usageGuideDescription");
  const preview = dialog?.querySelector(".usage-guide-preview");
  const acceptancePreview = document.getElementById("usageGuideAcceptancePreview");
  const recipientsPreview = document.getElementById("usageGuideRecipientsPreview");
  const messagesPreview = document.getElementById("usageGuideMessagesPreview");
  const repliesPreview = document.getElementById("usageGuideRepliesPreview");
  if (!trigger || !dialog || !closeButton || !previousButton || !nextButton || !stepLabel || !title || !description || !preview || !acceptancePreview || !recipientsPreview || !messagesPreview || !repliesPreview) return;

  const steps = [
    { name: "Connect", title: "No more manual Connect clicks", description: "BD used to open each LinkedIn profile and click Connect by hand. Now you provide the profile URLs, and the worker sends the invitations for you. This step removes that repetitive manual work from the outreach process." },
    { name: "Acceptance", title: "See who accepted your invitations", description: "Around a week after a Connect run, open Acceptance, select the week and click Check again on that Connect job. The worker checks who has accepted while you wait for the result. Checking once a week is usually enough; roughly 10% accepted after a week is an estimate, not a guaranteed rate." },
    { name: "Recipients", title: "Turn accepted connections into recipients", description: "Recipients gathers people confirmed as Accepted by the acceptance checks. Select a Connect week, then use Ready, Prepared and Sent to see where each person stands before or after messaging. Select Ready people and choose Prepare selected or Prepare all to create a recipient batch." },
    { name: "Messages", title: "Send personalized messages from prepared batches", description: "Open Messages and select a Prepared batch. Click Send messages, edit the prefilled template or write your own, then choose Queue & Send. The worker opens each recipient’s profile, replaces {first_name} with that person’s first name, and sends the message to the matching recipient." },
    { name: "Replies", title: "Manage replies from one inbox", description: "During each reply scan, the worker checks Unread for every Outreach account and matches sender names against profiles we successfully messaged. It reads matched conversation histories and syncs them into Replies. Choose the account and conversation, write your response, and confirm Send via worker to reply from that account to the matching LinkedIn profile." },
  ];
  let activeStep = 0;

  function showStep(index) {
    activeStep = index;
    const step = steps[index];
    stepLabel.textContent = `STEP ${String(index + 1).padStart(2, "0")} OF ${String(steps.length).padStart(2, "0")}`;
    title.textContent = step.title || step.name;
    description.textContent = step.description || `The ${step.name} guide is being prepared.`;
    preview.hidden = index !== 0;
    acceptancePreview.hidden = index !== 1;
    recipientsPreview.hidden = index !== 2;
    messagesPreview.hidden = index !== 3;
    repliesPreview.hidden = index !== 4;
    previousButton.disabled = index === 0;
    nextButton.disabled = index === steps.length - 1;

    dialog.classList.remove("is-playing");
    // Restart the illustration whenever a guide step appears.
    void dialog.offsetWidth;
    dialog.classList.add("is-playing");
  }

  trigger.addEventListener("click", () => {
    if (dialog.open) return;
    dialog.showModal();
    showStep(0);
    closeButton.focus();
  });

  const close = () => dialog.close();
  closeButton.addEventListener("click", close);
  previousButton.addEventListener("click", () => {
    if (activeStep > 0) showStep(activeStep - 1);
  });
  nextButton.addEventListener("click", () => {
    if (activeStep < steps.length - 1) showStep(activeStep + 1);
  });
  dialog.addEventListener("close", () => {
    dialog.classList.remove("is-playing");
    trigger.focus();
  });
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close();
  });
})();
