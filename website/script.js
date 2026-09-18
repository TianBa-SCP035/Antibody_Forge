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

const selectableContentSelector = [
  "input",
  "textarea",
  "select",
  "[contenteditable='true']",
  "pre",
  "code",
  "table",
  ".result-table-scroll",
  ".uniprot-entry",
  ".structure-entry",
  ".lab-output-block",
  ".alignment-output",
  ".molecule-sequence-map b",
].join(",");

document.addEventListener("selectstart", (event) => {
  if (event.target.closest?.(selectableContentSelector)) return;
  event.preventDefault();
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

const capabilityWorkspace = document.querySelector("[data-capability-workspace]");
const capabilityContent = capabilityWorkspace?.querySelector("[data-capability-content]");
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
    states: [
      "项目上下文已建立",
      "样本已进入发现主线",
      "候选序列已完成关联",
      "评价结果已回写证据链",
    ],
    steps: [
      {
        title: "建立项目边界与版本基线",
        description: "在实验开始前固定靶点、抗原版本、项目目标和责任团队，让后续对象从同一上下文出发。",
        input: "Target profile · Antigen version · Program owner",
        action: "创建项目对象、版本基线与阶段门禁",
        evidence: "Program VITA-024 · Scope v1.3",
      },
      {
        title: "让样本继承完整实验来源",
        description: "采样时间、动物队列、免疫方案和效价结果随样本一并进入筛选环节，不再依赖人工补充背景。",
        input: "Animal RM-17 · Day 28 · Titer result",
        action: "生成样本批次并继承免疫上下文",
        evidence: "Sample SMP-091 · Chain intact",
      },
      {
        title: "把实验命中锁定为分子版本",
        description: "阳性孔位、读段质控、VH/VL 配对和 CDR 注释共同形成可复现的候选序列版本。",
        input: "Well B07 · VH/VL reads · QC report",
        action: "完成链配对、注释和候选版本锁定",
        evidence: "Clone 024-7 · Sequence v2.1",
      },
      {
        title: "让评价结论回到候选主线",
        description: "表达批次、结合、功能与开发性结果汇聚到同一候选对象，直接支撑排序和 Go / No-Go 决策。",
        input: "RUN-2481 · Binding · Function · Developability",
        action: "汇总证据矩阵并保存决策快照",
        evidence: "Vita-RS-024 · GO · Snapshot 05",
      },
    ],
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
    states: [
      "锁定评价结果 Vita-RS-024",
      "定位实验运行批次 RUN-2481",
      "确认来源样本 SMP-091",
      "已回溯至完整项目上下文",
    ],
    steps: [
      {
        title: "从待解释结论开始追溯",
        description: "选择评价结果后，立即看到指标值、判定阈值、算法或人工结论以及对应结果版本。",
        input: "Vita-RS-024 · KD 1.8 nM · Functional hit",
        action: "锁定结果版本与判定依据",
        evidence: "Result snapshot · Reviewer · Timestamp",
      },
      {
        title: "定位产生结果的实验运行",
        description: "沿结果关系进入具体运行批次，查看方案、设备、板位、操作者与原始文件。",
        input: "Result ID · Assay type · Data file",
        action: "解析结果到运行批次的直接关系",
        evidence: "RUN-2481 · Plate P12 · QC passed",
      },
      {
        title: "确认样本、批次与上游来源",
        description: "将实验运行继续反向连接到蛋白批次、候选序列、阳性孔位与原始样本。",
        input: "RUN-2481 · Clone 024-7",
        action: "恢复样本与分子对象的完整谱系",
        evidence: "SMP-091 · Well B07 · Animal RM-17",
      },
      {
        title: "回到项目目标和历史决策",
        description: "最终回到项目边界、抗原版本和阶段决策，完整解释这个结果为何产生、如何被使用。",
        input: "Sample lineage · Decision history",
        action: "汇总双向谱系与版本时间线",
        evidence: "Program VITA-024 · Audit chain complete",
      },
    ],
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
    states: [
      "分析请求已创建",
      "责任团队已接单",
      "实验状态已同步",
      "交付物已完成跨团队交接",
    ],
    steps: [
      {
        title: "把口头需求转化为标准请求",
        description: "明确请求类型、目标对象、优先级、期望交付物和前置依赖，减少信息反复确认。",
        input: "Clone 024-7 · Expression request · Priority P1",
        action: "创建请求并校验必需上下文",
        evidence: "REQ-4102 · Ready for assignment",
      },
      {
        title: "将责任、时限和权限一次对齐",
        description: "责任团队接单时同时获得完整上游信息、服务时限和允许执行的操作范围。",
        input: "Request · Team capacity · Permission scope",
        action: "分配 Owner、SLA 与协作边界",
        evidence: "Expression team · Owner EX-07 · Due Sep 21",
      },
      {
        title: "让进度变化成为共享事实",
        description: "实验开始、等待、异常和完成状态由执行端持续更新，前后团队无需重复询问。",
        input: "Work order · Instrument event · Exception flag",
        action: "同步状态、阻塞原因和预计完成时间",
        evidence: "RUN-2481 · Purification · On schedule",
      },
      {
        title: "以可验收交付物完成交接",
        description: "下游团队接收的不只是完成提示，还包括批次、质控结果、文件和下一步建议。",
        input: "Batch result · QC package · Handoff checklist",
        action: "执行交付确认并触发下游任务",
        evidence: "Protein batch released · Characterization queued",
      },
    ],
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
    states: [
      "实验工单参数校验完成",
      "任务已下发至自动化设备",
      "设备运行完成，数据开始回传",
      "结果已归档至项目数据链",
    ],
    steps: [
      {
        title: "在下发前完成工单门禁",
        description: "系统检查样本、板位、体积、方法版本和设备能力，只有满足约束的工单才能进入队列。",
        input: "ORDER-731 · Plate P12 · Method ELISA-v4",
        action: "执行参数、依赖与资源可用性校验",
        evidence: "Validated · 12 checks passed · 0 blockers",
      },
      {
        title: "把结构化任务下发到正确设备",
        description: "通过设备适配层转换任务参数，保留工单、设备任务和项目对象之间的唯一关联。",
        input: "Validated order · Device profile · Queue priority",
        action: "生成设备任务并锁定执行版本",
        evidence: "DEVICE-A03 · JOB-9821 · Queued",
      },
      {
        title: "将运行状态和异常持续带回平台",
        description: "关键节点、进度、耗材和异常事件形成可观察时间线，支持人工接管与安全恢复。",
        input: "Telemetry · Runtime events · Exception codes",
        action: "监控运行、标记异常并保存处置记录",
        evidence: "RUN-2481 · 100% · QC gate passed",
      },
      {
        title: "让结果自动归档并触发下一步",
        description: "原始文件、结构化结果和质控结论回写到原工单与样本上下文，并生成后续评价任务。",
        input: "Raw files · Parsed result · QC decision",
        action: "回写结果、关闭工单并创建下游请求",
        evidence: "Vita-RS-024 · Archived · Next task created",
      },
    ],
  },
};
const capabilityKeys = Object.keys(capabilityDetails);
let activeCapabilityKey = "mainline";
const capabilityStepByKey = new Map(Object.keys(capabilityDetails).map((key) => [key, 0]));

const setCapabilityStep = (requestedIndex, focusTab = false) => {
  const detail = capabilityDetails[activeCapabilityKey];
  if (!capabilityWorkspace || !detail) return;
  const stepIndex = Math.max(0, Math.min(requestedIndex, detail.steps.length - 1));
  const step = detail.steps[stepIndex];
  capabilityStepByKey.set(activeCapabilityKey, stepIndex);

  const tabs = [...capabilityWorkspace.querySelectorAll("[data-capability-step]")];
  tabs.forEach((tab, index) => {
    const active = index === stepIndex;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  if (focusTab) tabs[stepIndex]?.focus();

  const values = {
    "[data-capability-step-index]": `STEP ${String(stepIndex + 1).padStart(2, "0")}`,
    "[data-capability-step-state]": detail.states[stepIndex],
    "[data-capability-step-title]": step.title,
    "[data-capability-step-description]": step.description,
    "[data-capability-step-input]": step.input,
    "[data-capability-step-action]": step.action,
    "[data-capability-step-evidence]": step.evidence,
  };
  Object.entries(values).forEach(([selector, value]) => {
    const target = capabilityWorkspace.querySelector(selector);
    if (target) target.textContent = value;
  });

  capabilityWorkspace.dataset.stageIndex = String(stepIndex);
  const routeProgress = capabilityWorkspace.querySelector("[data-capability-route-progress]");
  if (routeProgress) {
    const progress = 8 + (stepIndex / Math.max(1, detail.steps.length - 1)) * 92;
    routeProgress.style.strokeDasharray = `${progress} 100`;
  }

  const panel = capabilityWorkspace.querySelector("[data-capability-step-title]")?.closest("section");
  if (panel && !reducedMotion) {
    panel.animate(
      [
        { opacity: 0.55, transform: "translateY(5px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 180, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
    );
    panel.querySelectorAll(".story-card").forEach((card, index) => {
      card.animate(
        [
          { opacity: 0.35, filter: "blur(4px)" },
          { opacity: 1, filter: "blur(0)" },
        ],
        {
          duration: 280,
          delay: index * 45,
          easing: "cubic-bezier(0.22, 1, 0.36, 1)",
          fill: "both",
        },
      );
    });
  }
};

const buildCapabilityPath = (detail) => {
  const path = capabilityWorkspace?.querySelector("[data-capability-path]");
  if (!path) return;
  path.replaceChildren();

  detail.path.forEach((label, index) => {
    const button = document.createElement("button");
    const number = document.createElement("span");
    const name = document.createElement("strong");
    const state = document.createElement("small");
    button.type = "button";
    button.dataset.capabilityStep = String(index);
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "capability-step-detail");
    number.textContent = String(index + 1).padStart(2, "0");
    name.textContent = label;
    state.textContent = detail.states[index];
    button.append(number, name, state);
    button.addEventListener("click", () => setCapabilityStep(index));
    button.addEventListener("keydown", (event) => {
      let nextIndex;
      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        nextIndex = (index + 1) % detail.path.length;
      } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        nextIndex = (index - 1 + detail.path.length) % detail.path.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = detail.path.length - 1;
      }
      if (nextIndex === undefined) return;
      event.preventDefault();
      setCapabilityStep(nextIndex, true);
    });
    path.append(button);
  });
};

const setActiveCapability = (key, focusTab = false) => {
  const detail = capabilityDetails[key];
  if (!capabilityWorkspace || !detail) return;
  const previousIndex = capabilityKeys.indexOf(activeCapabilityKey);
  const nextIndex = capabilityKeys.indexOf(key);
  const changed = key !== activeCapabilityKey;
  activeCapabilityKey = key;

  capabilityTriggers.forEach((trigger) => {
    const active = trigger.dataset.capabilityTrigger === key;
    trigger.classList.toggle("active", active);
    trigger.setAttribute("aria-selected", String(active));
    trigger.tabIndex = active ? 0 : -1;
  });
  if (focusTab) capabilityWorkspace.querySelector(`[data-capability-trigger="${key}"]`)?.focus();
  capabilityContent?.setAttribute("aria-labelledby", `capability-tab-${key}`);
  const routeVisual = capabilityWorkspace.querySelector("[data-capability-visual]");
  if (routeVisual) routeVisual.dataset.capabilityMode = key;

  const values = {
    "[data-capability-tag]": detail.tag,
    "[data-capability-title]": detail.title,
    "[data-capability-description]": detail.description,
    "[data-capability-objects]": detail.objects,
    "[data-capability-control]": detail.control,
    "[data-capability-outcome]": detail.outcome,
    "[data-capability-panel-index]": `${String(nextIndex + 1).padStart(2, "0")} / ${String(
      capabilityKeys.length,
    ).padStart(2, "0")}`,
  };
  Object.entries(values).forEach(([selector, value]) => {
    const target = capabilityWorkspace.querySelector(selector);
    if (target) target.textContent = value;
  });

  buildCapabilityPath(detail);
  setCapabilityStep(capabilityStepByKey.get(key) ?? 0);
  if (changed && capabilityContent && !reducedMotion) {
    const direction = nextIndex >= previousIndex ? 1 : -1;
    capabilityContent.animate(
      [
        { opacity: 0.35, transform: `translateX(${direction * 26}px)` },
        { opacity: 1, transform: "translateX(0)" },
      ],
      { duration: 260, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
    );
  }
};

capabilityTriggers.forEach((trigger, index) => {
  trigger.addEventListener("click", () => {
    setActiveCapability(trigger.dataset.capabilityTrigger);
  });
  trigger.addEventListener("keydown", (event) => {
    let nextIndex;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      nextIndex = (index + 1) % capabilityKeys.length;
    } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      nextIndex = (index - 1 + capabilityKeys.length) % capabilityKeys.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = capabilityKeys.length - 1;
    }
    if (nextIndex === undefined) return;
    event.preventDefault();
    setActiveCapability(capabilityKeys[nextIndex], true);
  });
});

setActiveCapability(activeCapabilityKey);

const roleExplorer = document.querySelector("[data-role-explorer]");
const roleDetail = roleExplorer?.querySelector("[data-role-detail]");
const roleTriggers = [...(roleExplorer?.querySelectorAll("[data-role-trigger]") ?? [])];
const roleDetails = {
  im: {
    phase: "01 · IMMUNIZATION",
    title: "从抗原与动物队列建立发现入口",
    summary: "统一查看免疫方案、给药计划、笼位、采样和效价曲线，及时确定进入筛选的动物与样本。",
    receives: "抗原信息 · 项目目标 · 动物队列",
    acts: "免疫计划 · 采样 · 效价判断",
    delivers: "入选动物 · 样本批次 · 效价证据",
  },
  sb: {
    phase: "02 · SCREENING",
    title: "在完整来源上下文中识别阳性克隆",
    summary: "筛选团队直接读取动物、样本与效价背景，将门控条件、阳性孔位和复核结果写回同一候选链。",
    receives: "样本批次 · 效价结果 · 分选策略",
    acts: "单 B 筛选 · 门控复核 · 克隆选择",
    delivers: "阳性孔位 · 命中轨迹 · 候选样本",
  },
  ng: {
    phase: "03 · SEQUENCING",
    title: "把实验命中转化为可追踪的 VH / VL",
    summary: "序列团队围绕阳性孔位完成读段质控、链配对与候选注释，并保留序列和样本之间的双向关系。",
    receives: "阳性孔位 · 文库样本 · 测序读段",
    acts: "质控拼接 · VH/VL 配对 · 聚类注释",
    delivers: "候选序列 · 克隆簇 · 版本记录",
  },
  ex: {
    phase: "04 · EXPRESSION",
    title: "让每个蛋白批次都能回到原始序列",
    summary: "构建、转染、培养和纯化围绕候选序列展开，产量、纯度和异常状态随批次持续回传。",
    receives: "候选序列 · 载体模板 · 板位设计",
    acts: "构建转染 · 表达培养 · 纯化质检",
    delivers: "蛋白批次 · 产量纯度 · 质控状态",
  },
  qa: {
    phase: "05 · CHARACTERIZATION",
    title: "将分散实验结果收敛为候选决策",
    summary: "评价团队汇集结合、亲和力、功能与开发性证据，在同一版本快照中完成排序和 Go / No-Go 判断。",
    receives: "蛋白批次 · 实验方案 · 决策阈值",
    acts: "结合评价 · 功能验证 · 开发性复核",
    delivers: "证据矩阵 · 候选排序 · 决策记录",
  },
};
let roleTimer;

const setActiveRole = (key) => {
  const detail = roleDetails[key];
  if (!roleDetail || !detail) return;
  roleTriggers.forEach((trigger) => {
    const active = trigger.dataset.roleTrigger === key;
    trigger.classList.toggle("active", active);
    trigger.setAttribute("aria-selected", String(active));
  });
  window.clearTimeout(roleTimer);
  roleDetail.classList.add("is-updating");
  roleTimer = window.setTimeout(() => {
    const values = {
      "[data-role-phase]": detail.phase,
      "[data-role-title]": detail.title,
      "[data-role-summary]": detail.summary,
      "[data-role-receives]": detail.receives,
      "[data-role-acts]": detail.acts,
      "[data-role-delivers]": detail.delivers,
    };
    Object.entries(values).forEach(([selector, value]) => {
      const target = roleDetail.querySelector(selector);
      if (target) target.textContent = value;
    });
    roleDetail.classList.remove("is-updating");
  }, reducedMotion ? 0 : 100);
};

roleTriggers.forEach((trigger, index) => {
  trigger.addEventListener("click", () => setActiveRole(trigger.dataset.roleTrigger));
  trigger.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let targetIndex = index;
    if (event.key === "ArrowLeft") targetIndex = (index - 1 + roleTriggers.length) % roleTriggers.length;
    if (event.key === "ArrowRight") targetIndex = (index + 1) % roleTriggers.length;
    if (event.key === "Home") targetIndex = 0;
    if (event.key === "End") targetIndex = roleTriggers.length - 1;
    roleTriggers[targetIndex]?.focus();
    setActiveRole(roleTriggers[targetIndex]?.dataset.roleTrigger);
  });
});

const candidate = document.querySelector("[data-candidate]");
const candidateStory = candidate?.querySelector("[data-candidate-story]");
const candidateSteps = [...(candidate?.querySelectorAll("[data-candidate-step]") ?? [])];
const candidateLineageNodes = [...(candidate?.querySelectorAll(".candidate-lineage span") ?? [])];
const candidateLineageLinks = [...(candidate?.querySelectorAll(".candidate-lineage i") ?? [])];
const candidatePhases = [
  {
    phase: "PHASE 01 · IMMUNITY",
    title: "建立 VITA-024 的第一段实验上下文",
    state: "IN PROGRESS",
    summary: "抗原构建、免疫方案与动物队列进入同一项目对象，后续样本将自动继承该项目背景。",
    context: "Program VITA-024 · Antigen AG-024",
    contextNote: "项目目标、抗原版本与动物队列保持关联。",
    evidence: "免疫队列 IM-024 · 第 28 天效价",
    evidenceNote: "FACS / ELISA 结果形成可比较的响应曲线。",
    decision: "选择高应答动物进入单 B 筛选",
    decisionNote: "决策与阈值、操作者和时间一并留痕。",
    moleculeMode: "overview",
  },
  {
    phase: "PHASE 02 · SCREENING",
    title: "SMP-091 从阳性孔位进入候选主线",
    state: "HIT CONFIRMED",
    summary: "单 B 细胞筛选记录门控条件、孔位与复核结论，命中样本不再脱离其动物和免疫来源。",
    context: "VITA-024 · IM-024 · Animal RM-17",
    contextNote: "免疫响应、采样时间与筛选条件持续可查。",
    evidence: "Sample SMP-091 · Well B07 · Positive",
    evidenceNote: "阳性信号与门控快照形成筛选证据。",
    decision: "将命中样本送入 VH / VL 序列恢复",
    decisionNote: "筛选结论直接生成下游测序请求。",
    moleculeMode: "paratope",
  },
  {
    phase: "PHASE 03 · SEQUENCE",
    title: "VH / VL 配对将实验命中转化为分子对象",
    state: "SEQUENCE LOCKED",
    summary: "经过质控与配对的重链、轻链序列形成候选分子版本，并与 SMP-091 保持双向追溯。",
    context: "VITA-024 · SMP-091 · Well B07",
    contextNote: "原始读段、质控结果和样本来源保持关联。",
    evidence: "VITA-H024 · VITA-L024 · Clone 024-7",
    evidenceNote: "六段 CDR 与 VH / VL 版本完成注释。",
    decision: "锁定 024-7 并进入重组表达",
    decisionNote: "序列版本成为构建和表达批次的唯一来源。",
    moleculeMode: "sequence",
  },
  {
    phase: "PHASE 04 · EXPRESSION",
    title: "RUN-2481 将序列版本连接到蛋白实物",
    state: "QC PASSED",
    summary: "构建、转染、表达和纯化状态围绕 Clone 024-7 展开，蛋白批次携带完整序列与工艺上下文。",
    context: "Clone 024-7 · Vector VEC-31 · Plate P12",
    contextNote: "构建版本、细胞批次和板位可相互定位。",
    evidence: "RUN-2481 · Yield 32 mg/L · Purity 96.8%",
    evidenceNote: "演示批次产量、纯度与质控状态同步归档。",
    decision: "释放蛋白批次进入结合与功能评价",
    decisionNote: "通过状态门禁后自动生成评价任务。",
    moleculeMode: "overview",
  },
  {
    phase: "PHASE 05 · DECISION",
    title: "Vita-RS-024 汇聚为可解释的 Go 决策",
    state: "GO CANDIDATE",
    summary: "结合、亲和力、功能与开发性结果回到同一候选对象，团队可以从结论直接追至任一实验和样本。",
    context: "RUN-2481 · Clone 024-7 · SMP-091",
    contextNote: "最终结论继承完整实验、序列与批次谱系。",
    evidence: "Vita-RS-024 · KD 1.8 nM · Functional hit",
    evidenceNote: "演示结果展示亲和力与功能证据的联合收敛。",
    decision: "GO · 进入候选优化与扩展验证",
    decisionNote: "决策快照保留阈值、证据版本和参与角色。",
    moleculeMode: "binding",
  },
];
let activeCandidateIndex = 0;
let candidateTimer;

const setActiveCandidate = (requestedIndex) => {
  if (!candidateStory || !candidateSteps.length) return;
  const index = Math.max(0, Math.min(candidateSteps.length - 1, requestedIndex));
  const phase = candidatePhases[index];
  activeCandidateIndex = index;
  candidateSteps.forEach((step, stepIndex) => {
    const active = stepIndex === index;
    step.classList.toggle("active", active);
    step.setAttribute("aria-selected", String(active));
  });
  candidateLineageNodes.forEach((node, nodeIndex) => node.classList.toggle("active", nodeIndex <= index));
  candidateLineageLinks.forEach((link, linkIndex) => link.classList.toggle("active", linkIndex < index));
  window.clearTimeout(candidateTimer);
  candidateStory.classList.add("is-updating");
  candidateTimer = window.setTimeout(() => {
    const values = {
      "[data-candidate-phase]": phase.phase,
      "[data-candidate-title]": phase.title,
      "[data-candidate-state]": phase.state,
      "[data-candidate-summary]": phase.summary,
      "[data-candidate-context]": phase.context,
      "[data-candidate-context-note]": phase.contextNote,
      "[data-candidate-evidence]": phase.evidence,
      "[data-candidate-evidence-note]": phase.evidenceNote,
      "[data-candidate-decision]": phase.decision,
      "[data-candidate-decision-note]": phase.decisionNote,
      "[data-candidate-current]": String(index + 1).padStart(2, "0"),
    };
    Object.entries(values).forEach(([selector, value]) => {
      const target = candidateStory.querySelector(selector);
      if (target) target.textContent = value;
    });
    candidateStory.dataset.moleculeMode = phase.moleculeMode;
    candidateStory.classList.remove("is-updating");
  }, reducedMotion ? 0 : 110);
};

candidateSteps.forEach((step, index) => {
  step.addEventListener("click", () => {
    setActiveCandidate(index);
  });
  step.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let targetIndex = index;
    if (event.key === "ArrowLeft") targetIndex = Math.max(0, index - 1);
    if (event.key === "ArrowRight") targetIndex = Math.min(candidateSteps.length - 1, index + 1);
    if (event.key === "Home") targetIndex = 0;
    if (event.key === "End") targetIndex = candidateSteps.length - 1;
    candidateSteps[targetIndex]?.focus();
    setActiveCandidate(targetIndex);
  });
});

candidate?.querySelector("[data-candidate-prev]")?.addEventListener("click", () => {
  setActiveCandidate((activeCandidateIndex - 1 + candidatePhases.length) % candidatePhases.length);
});
candidate?.querySelector("[data-candidate-next]")?.addEventListener("click", () => {
  setActiveCandidate((activeCandidateIndex + 1) % candidatePhases.length);
});
candidate?.querySelector("[data-candidate-molecule]")?.addEventListener("click", () => {
  const phase = candidatePhases[activeCandidateIndex];
  document.dispatchEvent(
    new CustomEvent("vita:molecule-view", {
      detail: { mode: phase.moleculeMode, region: phase.moleculeMode === "sequence" ? "H3" : null },
    }),
  );
  document.querySelector("#experience")?.scrollIntoView({
    behavior: reducedMotion ? "auto" : "smooth",
    block: "start",
  });
});

document.querySelector("[data-workflow-case]")?.addEventListener("click", () => {
  setActiveCandidate(activeWorkflowIndex);
  candidate?.scrollIntoView({
    behavior: reducedMotion ? "auto" : "smooth",
    block: "start",
  });
});

const heroVisual = document.querySelector(".hero-visual");
const heroStages = [...(heroVisual?.querySelectorAll("[data-hero-stage], [data-hero-capability]") ?? [])];
const heroLines = [...(heroVisual?.querySelectorAll("[data-hero-line]") ?? [])];

const setHeroStageFocus = (key) => {
  heroStages.forEach((stage) => {
    const stageKey = stage.dataset.heroStage ?? stage.dataset.heroCapability;
    stage.classList.toggle("is-active", stageKey === key);
  });
  heroLines.forEach((line) => line.classList.toggle("is-active", line.dataset.heroLine === key));
};

heroStages.forEach((stage) => {
  const key = stage.dataset.heroStage ?? stage.dataset.heroCapability;
  stage.addEventListener("pointerenter", () => setHeroStageFocus(key));
  stage.addEventListener("pointerleave", () => setHeroStageFocus());
  stage.addEventListener("focus", () => setHeroStageFocus(key));
  stage.addEventListener("blur", () => setHeroStageFocus());
  stage.addEventListener("click", () => {
    if (stage.dataset.heroStage !== undefined) {
      workflowInteractionMode = "manual";
      setActiveWorkflowStep(Number(stage.dataset.heroStage));
      document.querySelector("#workflow")?.scrollIntoView({
        behavior: reducedMotion ? "auto" : "smooth",
        block: "start",
      });
      return;
    }
    setActiveCapability(stage.dataset.heroCapability);
    capabilityWorkspace?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "center",
    });
  });
});

heroVisual?.querySelector("[data-hero-case]")?.addEventListener("click", () => {
  setActiveCandidate(0);
  candidate?.scrollIntoView({
    behavior: reducedMotion ? "auto" : "smooth",
    block: "start",
  });
});

const ecosystem = document.querySelector("#ecosystem");
const ecosystemDetail = ecosystem?.querySelector("[data-ecosystem-detail]");
const ecosystemTriggers = [...(ecosystem?.querySelectorAll("[data-ecosystem-layer]") ?? [])];
const ecosystemDetails = {
  renmice: {
    tag: "BIOLOGICAL FOUNDATION",
    title: "RenMice® 提供全人抗体发现起点",
    description: "靶点人源化与全人抗体小鼠平台构成发现的生物学基础，为后续筛选与分子开发提供多样化来源。",
  },
  integrum: {
    tag: "SCALED ANTIBODY RESOURCE",
    title: "Project Integrum 沉淀规模化抗体资源",
    description: "“千鼠万抗”将广泛靶点与全人抗体资源持续积累，为候选检索、比较和后续开发建立规模基础。",
  },
  rensuper: {
    tag: "AI + AUTOMATED VALIDATION",
    title: "RenSuper™ 连接 AI 决策与高通量验证",
    description: "通过 AI 驱动的候选筛选与自动化实验验证，让大规模抗体资源更快收敛为可推进的研发选择。",
  },
  vita: {
    tag: "WORKFLOW + DATA FOUNDATION",
    title: "Antibody Vita 让实验、数据与协作连续发生",
    description: "本项目聚焦执行工单、研发对象、实验结果和团队交接，为相关发现场景提供可追溯的流程与数据基础。",
  },
};
let ecosystemTimer;

const setActiveEcosystemLayer = (key) => {
  const detail = ecosystemDetails[key];
  if (!ecosystemDetail || !detail) return;
  ecosystemTriggers.forEach((trigger) => {
    const active = trigger.dataset.ecosystemLayer === key;
    trigger.classList.toggle("active", active);
    trigger.setAttribute("aria-selected", String(active));
  });
  ecosystem.dataset.ecosystemActive = key;
  window.clearTimeout(ecosystemTimer);
  ecosystemDetail.classList.add("is-updating");
  ecosystemTimer = window.setTimeout(() => {
    const tag = ecosystemDetail.querySelector("[data-ecosystem-tag]");
    const title = ecosystemDetail.querySelector("[data-ecosystem-title]");
    const description = ecosystemDetail.querySelector("[data-ecosystem-description]");
    if (tag) tag.textContent = detail.tag;
    if (title) title.textContent = detail.title;
    if (description) description.textContent = detail.description;
    ecosystemDetail.classList.remove("is-updating");
  }, reducedMotion ? 0 : 100);
};

ecosystemTriggers.forEach((trigger, index) => {
  trigger.addEventListener("click", () => setActiveEcosystemLayer(trigger.dataset.ecosystemLayer));
  trigger.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const targetIndex =
      event.key === "ArrowRight"
        ? (index + 1) % ecosystemTriggers.length
        : (index - 1 + ecosystemTriggers.length) % ecosystemTriggers.length;
    ecosystemTriggers[targetIndex]?.focus();
    setActiveEcosystemLayer(ecosystemTriggers[targetIndex]?.dataset.ecosystemLayer);
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
