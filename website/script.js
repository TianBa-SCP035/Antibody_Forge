const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileNav = document.querySelector("[data-mobile-nav]");
const revealItems = document.querySelectorAll(".reveal");
const workflow = document.querySelector("[data-workflow]");
const workflowSteps = document.querySelectorAll("[data-step]");
const trackProgress = document.querySelector("[data-track-progress]");
const sectionNavLinks = document.querySelectorAll("[data-section-nav]");
const ecosystemOrbit = document.querySelector(".ecosystem-orbit");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let activeWorkflowIndex = 0;

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
  if (willOpen) mobileNav?.querySelector("a")?.focus();
});

mobileNav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || menuToggle?.getAttribute("aria-expanded") !== "true") return;
  closeMenu();
  menuToggle.focus();
});

window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMenu();
});

window.addEventListener("scroll", updateHeader, { passive: true });
document.addEventListener("visibilitychange", () => {
  document.body.classList.toggle("motion-paused", document.hidden);
});
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
  activeWorkflowIndex = index;
  workflowSteps.forEach((step, stepIndex) => {
    step.classList.toggle("active", stepIndex <= index);
  });

  if (!trackProgress || workflowSteps.length < 2) return;
  const percentage = (index / (workflowSteps.length - 1)) * 100;

  if (window.innerWidth <= 1050) {
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
  step.addEventListener("click", () => setActiveWorkflowStep(index));
});

window.addEventListener("resize", () => setActiveWorkflowStep(activeWorkflowIndex));

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

if (sectionNavLinks.length) {
  const sectionLinks = new Map();

  sectionNavLinks.forEach((link) => {
    const target = document.querySelector(link.getAttribute("href"));
    if (!target) return;
    const links = sectionLinks.get(target) ?? [];
    links.push(link);
    sectionLinks.set(target, links);
  });

  const sections = [...sectionLinks.keys()].sort((a, b) => a.offsetTop - b.offsetTop);
  let navFrame;

  const updateSectionNav = () => {
    const marker = window.scrollY + window.innerHeight * 0.34;
    const activeSection = [...sections].reverse().find((section) => section.offsetTop <= marker);

    sectionNavLinks.forEach((link) => {
      link.classList.remove("active");
      link.removeAttribute("aria-current");
    });
    sectionLinks.get(activeSection)?.forEach((link) => {
      link.classList.add("active");
      link.setAttribute("aria-current", "location");
    });
  };

  window.addEventListener(
    "scroll",
    () => {
      if (navFrame) return;
      navFrame = window.requestAnimationFrame(() => {
        updateSectionNav();
        navFrame = undefined;
      });
    },
    { passive: true },
  );

  window.addEventListener("resize", updateSectionNav);
  updateSectionNav();
}

if (ecosystemOrbit) {
  if (reducedMotion || !("IntersectionObserver" in window)) {
    ecosystemOrbit.classList.add("in-view");
  } else {
    const motionObserver = new IntersectionObserver(
      ([entry]) => ecosystemOrbit.classList.toggle("in-view", entry.isIntersecting),
      { rootMargin: "15% 0px", threshold: 0.08 },
    );
    motionObserver.observe(ecosystemOrbit);
  }
}

setActiveWorkflowStep(0);
