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
let headerFrame;

const requestHeaderUpdate = () => {
  if (headerFrame) return;
  headerFrame = window.requestAnimationFrame(() => {
    updateHeader();
    headerFrame = undefined;
  });
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
  requestHeaderUpdate();
});

window.addEventListener("scroll", requestHeaderUpdate, { passive: true });
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

const workflowInspector = document.querySelector("[data-workflow-inspector]");
const workflowPhases = [
  {
    phase: "PHASE 01 · IMMUNITY",
    title: "免疫与效价",
    summary: "建立抗原、动物、免疫计划与效价结果之间的第一段证据链。",
    input: "抗原 · 免疫方案 · 动物队列",
    process: "给药计划 · 采样 · FACS / ELISA",
    output: "效价曲线 · 入选动物 · 样本批次",
  },
  {
    phase: "PHASE 02 · SCREENING",
    title: "筛选与发现",
    summary: "让单 B 细胞与噬菌体展示等发现路径共享样本来源、筛选条件与命中记录。",
    input: "B 细胞样本 · 分选门控 · 文库设计",
    process: "单 B 细胞筛选 · 噬菌体展示 · 命中复核",
    output: "阳性克隆 · 筛选轨迹 · 初选候选",
  },
  {
    phase: "PHASE 03 · SEQUENCING",
    title: "文库与测序",
    summary: "把实验命中转化为经过质控、组装和配对的候选序列集合。",
    input: "阳性孔位 · 文库样本 · Sanger / NGS 读段",
    process: "序列质控 · 拼接配对 · 聚类与注释",
    output: "VH / VL 序列 · 克隆簇 · 候选清单",
  },
  {
    phase: "PHASE 04 · EXPRESSION",
    title: "表达与纯化",
    summary: "将候选序列映射到构建、转染、培养和纯化批次，持续记录产量与质量。",
    input: "候选序列 · 载体模板 · 板位设计",
    process: "构建 · 转染 · 表达 · 纯化与质检",
    output: "质粒与细胞 · 蛋白批次 · 产量纯度",
  },
  {
    phase: "PHASE 05 · CHARACTERIZATION",
    title: "评价与决策",
    summary: "汇集结合、亲和力、功能及成药性证据，让候选排序与决策依据保持同步。",
    input: "蛋白批次 · 实验方案 · 对照与阈值",
    process: "结合 · 亲和力 · 功能 · 开发性评价",
    output: "证据矩阵 · 候选排序 · Go / No-Go 决策",
  },
];
let workflowInspectorTimer;
let workflowInteractionMode = "scroll";

const updateWorkflowInspector = (index) => {
  if (!workflowInspector) return;
  const phase = workflowPhases[index];
  if (!phase) return;

  window.clearTimeout(workflowInspectorTimer);
  workflowInspector.classList.add("is-updating");
  workflowInspectorTimer = window.setTimeout(() => {
    const values = {
      "[data-workflow-phase]": phase.phase,
      "[data-workflow-title]": phase.title,
      "[data-workflow-summary]": phase.summary,
      "[data-workflow-input]": phase.input,
      "[data-workflow-process]": phase.process,
      "[data-workflow-output]": phase.output,
      "[data-workflow-current]": String(index + 1).padStart(2, "0"),
    };
    Object.entries(values).forEach(([selector, value]) => {
      const target = workflowInspector.querySelector(selector);
      if (target) target.textContent = value;
    });
    workflowInspector.classList.remove("is-updating");
  }, reducedMotion ? 0 : 110);
};

const setActiveWorkflowStep = (requestedIndex) => {
  if (!workflowSteps.length) return;
  const index = Math.max(0, Math.min(workflowSteps.length - 1, requestedIndex));
  activeWorkflowIndex = index;
  workflowSteps.forEach((step, stepIndex) => {
    step.classList.toggle("active", stepIndex <= index);
    step.classList.toggle("selected", stepIndex === index);
    step.setAttribute("aria-pressed", String(stepIndex === index));
  });
  updateWorkflowInspector(index);

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
  step.addEventListener("mouseenter", () => {
    if (workflowInteractionMode !== "manual") workflowInteractionMode = "hover";
    setActiveWorkflowStep(index);
  });
  step.addEventListener("focusin", () => {
    workflowInteractionMode = "manual";
    setActiveWorkflowStep(index);
  });
  step.addEventListener("click", () => {
    workflowInteractionMode = "manual";
    setActiveWorkflowStep(index);
  });
  step.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let targetIndex = index;
    if (event.key === "ArrowLeft") targetIndex = Math.max(0, index - 1);
    if (event.key === "ArrowRight") targetIndex = Math.min(workflowSteps.length - 1, index + 1);
    if (event.key === "Home") targetIndex = 0;
    if (event.key === "End") targetIndex = workflowSteps.length - 1;
    workflowInteractionMode = "manual";
    workflowSteps[targetIndex]?.focus();
    setActiveWorkflowStep(targetIndex);
  });
});

workflowInspector?.querySelector("[data-workflow-prev]")?.addEventListener("click", () => {
  workflowInteractionMode = "manual";
  setActiveWorkflowStep((activeWorkflowIndex - 1 + workflowSteps.length) % workflowSteps.length);
});

workflowInspector?.querySelector("[data-workflow-next]")?.addEventListener("click", () => {
  workflowInteractionMode = "manual";
  setActiveWorkflowStep((activeWorkflowIndex + 1) % workflowSteps.length);
});

workflow?.addEventListener("mouseleave", () => {
  if (workflowInteractionMode === "hover") workflowInteractionMode = "scroll";
});

window.addEventListener("resize", () => setActiveWorkflowStep(activeWorkflowIndex));

if (workflow && "IntersectionObserver" in window) {
  const workflowObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          workflowInteractionMode = "scroll";
          return;
        }
        if (workflowInteractionMode !== "scroll") return;
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

const capabilityConsole = document.querySelector("[data-capability-console]");
const capabilityTriggers = document.querySelectorAll("[data-capability-trigger]");
const capabilityDetails = {
  mainline: {
    tag: "DISCOVERY MAINLINE · CONNECTED OBJECTS",
    title: "研发对象沿主线持续携带上下文",
    description:
      "项目、样本、序列、表达批次与评价结果通过同一对象关系向前传递，阶段切换不会丢失来源与决策依据。",
    objects: "PROJECT · SAMPLE · SEQUENCE · ASSAY",
    control: "阶段状态 · 依赖校验 · 版本记录",
    outcome: "连续、可查询的候选证据链",
    path: ["PROJECT", "SAMPLE", "SEQUENCE", "ASSAY"],
  },
  traceability: {
    tag: "TRACEABILITY · BIDIRECTIONAL LINEAGE",
    title: "从结果回到实验，从实验追至来源",
    description:
      "任一评价结果都可沿运行批次、实验样本和项目上下文反向定位，同时保留操作者、时间与版本信息。",
    objects: "RESULT · RUN · SAMPLE · PROJECT",
    control: "版本快照 · 操作记录 · 变更时间线",
    outcome: "快速审计、异常定位与科学复盘",
    path: ["RESULT", "RUN", "SAMPLE", "PROJECT"],
  },
  collaboration: {
    tag: "COLLABORATION · SHARED EXECUTION",
    title: "跨团队交接成为可见、可推进的执行链",
    description:
      "请求、责任人、状态与交付物在同一界面同步，前后环节可以直接读取所需信息并继续推进。",
    objects: "REQUEST · OWNER · STATUS · DELIVERABLE",
    control: "权限边界 · 状态门禁 · 交接确认",
    outcome: "更少等待与重复沟通，更清晰的进度",
    path: ["REQUEST", "OWNER", "STATUS", "HANDOFF"],
  },
  automation: {
    tag: "AUTOMATION · CLOSED-LOOP EXECUTION",
    title: "工单、设备运行与结果回写形成闭环",
    description:
      "经过校验的实验工单进入设备执行队列，运行状态和数据结果自动回到对应项目与样本上下文。",
    objects: "ORDER · DEVICE · RUN · RESULT",
    control: "参数校验 · 队列状态 · 异常标记",
    outcome: "稳定执行、实时进度与自动数据归档",
    path: ["ORDER", "DEVICE", "RUN", "RESULT"],
  },
};
let capabilityTimer;

const setActiveCapability = (key, revealConsole = false) => {
  const detail = capabilityDetails[key];
  if (!capabilityConsole || !detail) return;

  capabilityTriggers.forEach((trigger) => {
    const active = trigger.dataset.capabilityTrigger === key;
    trigger.classList.toggle("active", active);
    trigger.setAttribute("aria-pressed", String(active));
  });

  window.clearTimeout(capabilityTimer);
  capabilityConsole.classList.add("is-updating");
  capabilityTimer = window.setTimeout(() => {
    const values = {
      "[data-capability-tag]": detail.tag,
      "[data-capability-title]": detail.title,
      "[data-capability-description]": detail.description,
      "[data-capability-objects]": detail.objects,
      "[data-capability-control]": detail.control,
      "[data-capability-outcome]": detail.outcome,
    };
    Object.entries(values).forEach(([selector, value]) => {
      const target = capabilityConsole.querySelector(selector);
      if (target) target.textContent = value;
    });

    const path = capabilityConsole.querySelector("[data-capability-path]");
    if (path) {
      path.replaceChildren();
      detail.path.forEach((label, index) => {
        const node = document.createElement("span");
        node.textContent = label;
        path.append(node);
        if (index < detail.path.length - 1) path.append(document.createElement("i"));
      });
    }
    capabilityConsole.classList.remove("is-updating");
  }, reducedMotion ? 0 : 110);

  if (revealConsole) {
    window.setTimeout(() => {
      capabilityConsole.scrollIntoView({
        behavior: reducedMotion ? "auto" : "smooth",
        block: "center",
      });
    }, reducedMotion ? 0 : 130);
  }
};

capabilityTriggers.forEach((trigger) => {
  trigger.addEventListener("click", () => {
    setActiveCapability(trigger.dataset.capabilityTrigger, true);
  });
});

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
