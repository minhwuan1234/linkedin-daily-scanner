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
  const pendingStep = document.getElementById("usageGuidePendingStep");
  const pendingNumber = document.getElementById("usageGuidePendingNumber");
  if (!trigger || !dialog || !closeButton || !previousButton || !nextButton || !stepLabel || !title || !description || !preview || !acceptancePreview || !pendingStep || !pendingNumber) return;

  const steps = [
    { name: "Connect", title: "No more manual Connect clicks", description: "BD used to open each LinkedIn profile and click Connect by hand. Now you provide the profile URLs, and the worker sends the invitations for you. This step removes that repetitive manual work from the outreach process." },
    { name: "Acceptance", title: "See who accepted your invitations", description: "Around a week after a Connect run, open Acceptance, select the week and click Check again on that Connect job. The worker checks who has accepted while you wait for the result. Checking once a week is usually enough; roughly 10% accepted after a week is an estimate, not a guaranteed rate." },
    { name: "Recipients" },
    { name: "Messages" },
    { name: "Replies" },
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
    pendingStep.hidden = index < 2;
    pendingNumber.textContent = String(index + 1).padStart(2, "0");
    previousButton.disabled = index === 0;
    nextButton.disabled = index === steps.length - 1;

    dialog.classList.remove("is-playing");
    if (index < 2) {
      // Restart the illustration when either completed guide appears.
      void dialog.offsetWidth;
      dialog.classList.add("is-playing");
    }
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
