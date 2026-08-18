document.addEventListener("DOMContentLoaded", () => {
  const detailLinks = document.querySelectorAll(
    'a[href*="recipe_examples/"]'
  );

  if (!detailLinks.length) {
    return;
  }

  const modal = document.createElement("div");
  modal.className = "oceanval-recipe-modal";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="oceanval-recipe-modal__backdrop" data-close-recipe-modal></div>
    <section class="oceanval-recipe-modal__dialog" role="dialog"
      aria-modal="true" aria-labelledby="oceanval-recipe-modal-title">
      <div class="oceanval-recipe-modal__header">
        <h2 id="oceanval-recipe-modal-title">Recipe details</h2>
        <button type="button" class="oceanval-recipe-modal__close"
          aria-label="Close recipe details" data-close-recipe-modal>&times;</button>
      </div>
      <iframe title="Recipe details" class="oceanval-recipe-modal__frame"></iframe>
    </section>
  `;
  document.body.appendChild(modal);

  const frame = modal.querySelector(".oceanval-recipe-modal__frame");
  const close = () => {
    modal.hidden = true;
    document.body.classList.remove("oceanval-modal-open");
    frame.src = "about:blank";
  };

  detailLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      frame.src = link.href;
      modal.hidden = false;
      document.body.classList.add("oceanval-modal-open");
      modal.querySelector(".oceanval-recipe-modal__close").focus();
    });
  });

  modal.addEventListener("click", (event) => {
    if (event.target.hasAttribute("data-close-recipe-modal")) {
      close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) {
      close();
    }
  });
});
