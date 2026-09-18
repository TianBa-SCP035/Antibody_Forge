document.documentElement.classList.replace("no-js", "js-ready");

const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileNav = document.querySelector("[data-mobile-nav]");
const revealItems = document.querySelectorAll(".reveal");
const workflow = document.querySelector("[data-workflow]");
const workflowSteps = document.querySelectorAll("[data-step]");
const trackProgress = document.querySelector("[data-track-progress]");
const sectionNavLinks = document.querySelectorAll("[data-section-nav]");
const pageProgress = document.querySelector("[data-scroll-progress-rail]");
const cursorAura = document.querySelector("[data-cursor-aura]");
const cursorRing = document.querySelector("[data-cursor-ring]");
const cursorDot = document.querySelector("[data-cursor-dot]");
const quickTools = document.querySelector("[data-quick-tools]");
const quickToolsTrigger = document.querySelector("[data-quick-tools-trigger]");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const precisePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
let activeWorkflowIndex = 0;

const updateHeader = () => {
  header?.classList.toggle("scrolled", window.scrollY > 24);
  if (!pageProgress) return;
  const available = document.documentElement.scrollHeight - window.innerHeight;
  const progress = available > 0 ? Math.min(1, Math.max(0, window.scrollY / available)) : 0;
  pageProgress.style.transform = `scaleY(${progress})`;
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

const closeQuickTools = () => {
  if (!quickTools || !quickToolsTrigger) return;
  quickTools.classList.remove("open");
  quickToolsTrigger.setAttribute("aria-expanded", "false");
  quickToolsTrigger.setAttribute("aria-label", "打开工具快捷入口");
};

quickToolsTrigger?.addEventListener("click", () => {
  const willOpen = !quickTools.classList.contains("open");
  quickTools.classList.toggle("open", willOpen);
  quickToolsTrigger.setAttribute("aria-expanded", String(willOpen));
  quickToolsTrigger.setAttribute("aria-label", willOpen ? "关闭工具快捷入口" : "打开工具快捷入口");
});

quickTools?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeQuickTools);
});

document.addEventListener("pointerdown", (event) => {
  if (quickTools?.classList.contains("open") && !quickTools.contains(event.target)) {
    closeQuickTools();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (menuToggle?.getAttribute("aria-expanded") === "true") {
    closeMenu();
    menuToggle.focus();
  }
  if (quickTools?.classList.contains("open")) {
    closeQuickTools();
    quickToolsTrigger.focus();
  }
});

window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMenu();
});

window.addEventListener("scroll", updateHeader, { passive: true });
document.addEventListener("visibilitychange", () => {
  document.body.classList.toggle("motion-paused", document.hidden);
});
updateHeader();

if (!reducedMotion && precisePointer) {
  if (cursorAura && cursorRing && cursorDot) {
    document.documentElement.classList.add("cursor-enabled");
    let cursorFrame;
    let pointerX = -400;
    let pointerY = -400;
    let ringX = -400;
    let ringY = -400;
    let auraX = -400;
    let auraY = -400;
    let cursorVisible = false;
    let cursorInteractive = false;
    const activeBursts = [];

    const renderCursor = () => {
      ringX += (pointerX - ringX) * 0.22;
      ringY += (pointerY - ringY) * 0.22;
      auraX += (pointerX - auraX) * 0.11;
      auraY += (pointerY - auraY) * 0.11;
      cursorRing.style.transform = `translate3d(${ringX - 17}px, ${ringY - 17}px, 0)`;
      cursorDot.style.transform = `translate3d(${pointerX - 3}px, ${pointerY - 3}px, 0)`;
      cursorAura.style.transform = `translate3d(${auraX - 180}px, ${auraY - 180}px, 0)`;

      const ringSettling = Math.abs(pointerX - ringX) > 0.1 || Math.abs(pointerY - ringY) > 0.1;
      const auraSettling = Math.abs(pointerX - auraX) > 0.2 || Math.abs(pointerY - auraY) > 0.2;
      if (ringSettling || auraSettling) {
        cursorFrame = window.requestAnimationFrame(renderCursor);
      } else {
        cursorFrame = undefined;
      }
    };

    const setCursorState = (visible, interactive) => {
      if (visible !== cursorVisible) {
        cursorVisible = visible;
        cursorAura.classList.toggle("visible", visible);
        cursorRing.classList.toggle("visible", visible);
        cursorDot.classList.toggle("visible", visible);
      }
      if (interactive !== cursorInteractive) {
        cursorInteractive = interactive;
        cursorRing.classList.toggle("interactive", interactive);
        cursorDot.classList.toggle("interactive", interactive);
      }
    };

    const createPointerBurst = (event) => {
      if (event.button !== 0 || event.target.closest?.("input, textarea, select")) return;
      if (activeBursts.length >= 8) activeBursts.shift()?.remove();
      const burst = document.createElement("span");
      burst.className = "pointer-burst";
      burst.style.left = `${event.clientX}px`;
      burst.style.top = `${event.clientY}px`;
      burst.setAttribute("aria-hidden", "true");
      document.body.append(burst);
      activeBursts.push(burst);
      burst.addEventListener(
        "animationend",
        () => {
          burst.remove();
          const index = activeBursts.indexOf(burst);
          if (index >= 0) activeBursts.splice(index, 1);
        },
        { once: true },
      );
    };

    window.addEventListener(
      "pointermove",
      (event) => {
        pointerX = event.clientX;
        pointerY = event.clientY;
        const overTextField = Boolean(event.target.closest?.("input, textarea, select"));
        const overInteractive = Boolean(
          event.target.closest?.(
            "a, button, [role='button'], .pointer-tilt, [data-molecule-stage]",
          ),
        );
        setCursorState(!overTextField, overInteractive && !overTextField);
        if (!cursorFrame) cursorFrame = window.requestAnimationFrame(renderCursor);
      },
      { passive: true },
    );

    window.addEventListener(
      "pointerdown",
      (event) => {
        if (event.button !== 0) return;
        cursorRing.classList.add("pressed");
        createPointerBurst(event);
      },
      { passive: true },
    );
    window.addEventListener("pointerup", () => cursorRing.classList.remove("pressed"), {
      passive: true,
    });

    document.documentElement.addEventListener("mouseleave", () => {
      cursorVisible = false;
      cursorInteractive = false;
      cursorAura.classList.remove("visible");
      cursorRing.classList.remove("visible", "pressed");
      cursorRing.classList.remove("interactive");
      cursorDot.classList.remove("visible", "interactive");
    });
  }

  const tiltTargets = document.querySelectorAll(
    ".capability-card, .service-card",
  );

  tiltTargets.forEach((target) => {
    target.classList.add("pointer-tilt");
    let tiltFrame;
    let bounds;
    let nextX = 0;
    let nextY = 0;

    target.addEventListener("pointerenter", () => {
      bounds = target.getBoundingClientRect();
    });

    target.addEventListener("pointermove", (event) => {
      bounds ??= target.getBoundingClientRect();
      const relativeX = (event.clientX - bounds.left) / bounds.width;
      const relativeY = (event.clientY - bounds.top) / bounds.height;
      nextX = relativeX;
      nextY = relativeY;
      target.classList.add("pointer-active");
      if (tiltFrame) return;
      tiltFrame = window.requestAnimationFrame(() => {
        target.style.setProperty("--spot-x", `${(nextX * 100).toFixed(1)}%`);
        target.style.setProperty("--spot-y", `${(nextY * 100).toFixed(1)}%`);
        target.style.setProperty("--tilt-x", `${((0.5 - nextY) * 2.4).toFixed(2)}deg`);
        target.style.setProperty("--tilt-y", `${((nextX - 0.5) * 2.4).toFixed(2)}deg`);
        tiltFrame = undefined;
      });
    });

    target.addEventListener("pointerleave", () => {
      bounds = undefined;
      target.classList.remove("pointer-active");
      target.style.setProperty("--tilt-x", "0deg");
      target.style.setProperty("--tilt-y", "0deg");
      target.style.setProperty("--spot-x", "50%");
      target.style.setProperty("--spot-y", "50%");
    });
  });

  const parallaxStage = document.querySelector(".hero, .tools-hero");
  const parallaxVisual = parallaxStage?.querySelector(".hero-visual, .tools-hero-visual");
  if (parallaxStage && parallaxVisual) {
    let parallaxFrame;
    let parallaxBounds;
    let moveX = 0;
    let moveY = 0;

    parallaxStage.addEventListener("pointerenter", () => {
      parallaxBounds = parallaxStage.getBoundingClientRect();
    });

    parallaxStage.addEventListener("pointermove", (event) => {
      parallaxBounds ??= parallaxStage.getBoundingClientRect();
      moveX = ((event.clientX - parallaxBounds.left) / parallaxBounds.width - 0.5) * 12;
      moveY = ((event.clientY - parallaxBounds.top) / parallaxBounds.height - 0.5) * 12;
      if (parallaxFrame) return;
      parallaxFrame = window.requestAnimationFrame(() => {
        parallaxVisual.style.translate = `${moveX.toFixed(1)}px ${moveY.toFixed(1)}px`;
        parallaxFrame = undefined;
      });
    });

    parallaxStage.addEventListener("pointerleave", () => {
      parallaxBounds = undefined;
      parallaxVisual.style.translate = "0 0";
    });
  }
}

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

const countElements = document.querySelectorAll("[data-count-end]");

if (!reducedMotion && "IntersectionObserver" in window && countElements.length) {
  const countObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const element = entry.target;
        const endValue = Number(element.dataset.countEnd);
        const suffix = element.dataset.countSuffix ?? "";
        const textNode = element.firstChild;
        const startedAt = performance.now();
        const duration = 1050;

        const updateCount = (now) => {
          const progress = Math.min(1, (now - startedAt) / duration);
          const eased = 1 - (1 - progress) ** 3;
          const current = Math.round(endValue * eased);
          if (textNode) textNode.nodeValue = `${current.toLocaleString()}${suffix}`;
          if (progress < 1) window.requestAnimationFrame(updateCount);
        };

        window.requestAnimationFrame(updateCount);
        observer.unobserve(element);
      });
    },
    { threshold: 0.55 },
  );

  countElements.forEach((element) => countObserver.observe(element));
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

  const sections = [
    ...new Set([...sectionLinks.keys(), ...document.querySelectorAll("[data-nav-break]")]),
  ].sort((a, b) => a.offsetTop - b.offsetTop);
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

setActiveWorkflowStep(0);
