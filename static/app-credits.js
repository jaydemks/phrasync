"use strict";

// One registry for the welcome panel and full credits. Display names are
// intentional: never derive a legal name or donation amount from an account.
const PHRASYNC_CREDITS = Object.freeze({
  community: Object.freeze([
    Object.freeze({ name: "Especiel-EA", source: "GitHub", tier: "community" }),
    Object.freeze({ name: "jrod-86", source: "GitHub", tier: "community" }),
    Object.freeze({ name: "toxrocks", source: "GitHub", tier: "community" }),
    Object.freeze({ name: "alwayslove977", source: "GitHub", tier: "community" }),
    Object.freeze({ name: "@impalermusic", source: "Instagram & email", tier: "diamond" }),
  ]),
  supporters: Object.freeze([
    Object.freeze({ name: "Stefano A.", source: "Buy Me a Coffee", tier: "supporter" }),
  ]),
});

Object.assign(ITALIAN, {
  "PHRASYNC COMMUNITY": "COMMUNITY PHRASYNC",
  "Credits & supporters": "Crediti e sostenitori",
  "The people behind the progress": "Le persone che ci aiutano a crescere",
  "Made better, together.": "Insieme, sempre meglio.",
  "Thank you for helping Phrasync grow.": "Grazie per far crescere Phrasync.",
  "Community": "Community",
  "Financial support": "Supporto economico",
  "Community Contributors": "Contributori della community",
  "Diamond Contributors": "Contributori Diamond",
  "Supporters": "Sostenitori",
  "Diamond Supporters": "Sostenitori Diamond",
  "Testing, bug reports and ideas.": "Test, segnalazioni di bug e idee.",
  "Exceptional ongoing feedback and testing.": "Un aiuto costante e prezioso con feedback e test.",
  "Helping keep Phrasync free for everyone.": "Un aiuto per mantenere Phrasync gratuito per tutti.",
  "Extraordinary financial support.": "Un sostegno economico straordinario.",
  "A place for future Diamond Supporters.": "Uno spazio per i futuri sostenitori Diamond.",
  "Every contribution makes a difference.": "Ogni contributo fa la differenza.",
  "Feedback, testing and financial support all help this independent project grow.": "Feedback, test e supporto economico fanno crescere questo progetto indipendente.",
  "All features stay free. Supporting Phrasync is always optional.": "Tutte le funzioni restano gratuite. Sostenere Phrasync è sempre facoltativo.",
  "We use chosen display names or initials, never a full surname without permission.": "Usiamo nomi pubblici scelti o iniziali, mai il cognome completo senza consenso.",
  "Instagram & email": "Instagram ed email",
  "View all credits": "Vedi tutti i crediti",
  "Back to welcome": "Torna al benvenuto",
});

function creditGem() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 32 32");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(svg.namespaceURI, "path");
  path.setAttribute("d", "M9 5h14l6 9-13 14L3 14 9 5Zm-6 9h26M9 5l7 23L23 5M9 5l7 9 7-9");
  svg.append(path);
  return svg;
}

function creditText(tag, text, className = "") {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function creditGroup(title, description, entries, diamond = false, emptyText = "") {
  const section = document.createElement("section");
  section.className = `credit-tier${diamond ? " credit-tier-diamond" : ""}${entries.length ? "" : " credit-tier-empty"}`;
  const heading = document.createElement("div");
  heading.className = "credit-tier-heading";
  const mark = document.createElement("span");
  mark.className = "credit-mark";
  if (diamond) mark.append(creditGem());
  else { mark.textContent = "✦"; mark.setAttribute("aria-hidden", "true"); }
  heading.append(mark, creditText("h4", title));
  section.append(heading, creditText("p", description, "credit-tier-description"));
  if (!entries.length) section.append(creditText("p", emptyText, "credit-empty"));
  else {
    const list = document.createElement("ul");
    list.className = "credit-people";
    for (const person of entries) {
      const item = document.createElement("li");
      const name = creditText("strong", person.name);
      name.dataset.noI18n = "";
      item.append(name, creditText("span", person.source, "credit-source"));
      list.append(item);
    }
    section.append(list);
  }
  return section;
}

function renderCredits(root, compact = false) {
  const community = document.createElement("section");
  community.className = "credit-category";
  community.append(creditText("h3", "Community", "credit-category-label"));
  community.append(creditGroup("Diamond Contributors", "Exceptional ongoing feedback and testing.", PHRASYNC_CREDITS.community.filter(person => person.tier === "diamond"), true));
  community.append(creditGroup("Community Contributors", "Testing, bug reports and ideas.", PHRASYNC_CREDITS.community.filter(person => person.tier === "community")));
  const supporters = document.createElement("section");
  supporters.className = "credit-category";
  supporters.append(creditText("h3", "Financial support", "credit-category-label"));
  const diamondSupporters = PHRASYNC_CREDITS.supporters.filter(person => person.tier === "diamond");
  if (diamondSupporters.length) supporters.append(creditGroup("Diamond Supporters", "Extraordinary financial support.", diamondSupporters, true));
  supporters.append(creditGroup("Supporters", "Helping keep Phrasync free for everyone.", PHRASYNC_CREDITS.supporters.filter(person => person.tier === "supporter")));
  if (!compact && !diamondSupporters.length) supporters.append(creditGroup("Diamond Supporters", "Extraordinary financial support.", [], true, "A place for future Diamond Supporters."));
  root.replaceChildren(community, supporters);
}

function initCredits() {
  const welcome = document.getElementById("onboardingDialog");
  const dialog = document.getElementById("creditsDialog");
  const back = document.getElementById("creditsBack");
  let opener = null;
  renderCredits(document.getElementById("welcomeCredits"), true);
  renderCredits(document.getElementById("fullCredits"));
  document.querySelectorAll("[data-open-credits]").forEach(button => button.addEventListener("click", () => {
    if (dialog.open) return;
    opener = button;
    // Keep the underlying modal open: closing credits returns to the same
    // welcome/settings panel without changing its state or saved preferences.
    back.hidden = !welcome.open;
    dialog.showModal();
  }));
  document.querySelectorAll("[data-close-credits]").forEach(button => button.addEventListener("click", () => dialog.close()));
  dialog.addEventListener("close", () => {
    if (opener?.isConnected) {
      const target = opener.closest("details:not([open])")?.querySelector("summary") || opener;
      target.focus({ preventScroll: true });
    }
    opener = null;
  });
}
