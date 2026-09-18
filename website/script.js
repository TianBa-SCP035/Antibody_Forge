const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileNav = document.querySelector("[data-mobile-nav]");
const revealItems = document.querySelectorAll(".reveal");
const workflow = document.querySelector("[data-workflow]");
const workflowSteps = document.querySelectorAll("[data-step]");
const trackProgress = document.querySelector("[data-track-progress]");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const updateHeader = () => {
  header?.classList.toggle("scrolled", window.scrollY > 24);
};

const closeMenu = () => {
  if (!menuToggle || !mobileNav) return;
  menuToggle.setAttribute("aria-expanded", "false");
  menuToggle.setAttribute("aria-label", "打开导航菜单");
  mobileNav.classList.remove("open");
  document.body.classList.remove("menu-open");
};

menuToggle?.addEventListener("click", () => {
  const willOpen = menuToggle.getAttribute("aria-expanded") !== "true";
  menuToggle.setAttribute("aria-expanded", String(willOpen));
  menuToggle.setAttribute("aria-label", willOpen ? "关闭导航菜单" : "打开导航菜单");
  mobileNav?.classList.toggle("open", willOpen);
  document.body.classList.toggle("menu-open", willOpen);
});

mobileNav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMenu();
});

window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();

if (reducedMotion || !("IntersectionObserver" in window)) {
  revealItems.forEach((item) => item.classList.add("visible"));
} else {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -5% 0px" },
  );

  revealItems.forEach((item) => revealObserver.observe(item));
}

const setActiveWorkflowStep = (index) => {
  workflowSteps.forEach((step, stepIndex) => {
    step.classList.toggle("active", stepIndex <= index);
  });

  if (!trackProgress || workflowSteps.length < 2) return;
  const percentage = (index / (workflowSteps.length - 1)) * 100;

  if (window.innerWidth <= 900) {
    trackProgress.style.width = "1px";
    trackProgress.style.height = `${percentage}%`;
  } else {
    trackProgress.style.width = `${percentage}%`;
    trackProgress.style.height = "1px";
  }
};

workflowSteps.forEach((step, index) => {
  step.addEventListener("mouseenter", () => setActiveWorkflowStep(index));
  step.addEventListener("focusin", () => setActiveWorkflowStep(index));
});

if (workflow && "IntersectionObserver" in window) {
  const workflowObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const progress = Math.min(
          1,
          Math.max(0, (window.innerHeight - entry.boundingClientRect.top) / window.innerHeight),
        );
        const index = Math.min(
          workflowSteps.length - 1,
          Math.floor(progress * workflowSteps.length),
        );
        setActiveWorkflowStep(index);
      });
    },
    { threshold: [0.15, 0.35, 0.55, 0.75] },
  );

  workflowObserver.observe(workflow);
}

setActiveWorkflowStep(0);
