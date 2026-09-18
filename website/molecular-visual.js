(() => {
  const stage = document.querySelector("[data-molecule-stage]");
  const canvas = document.querySelector("[data-molecule-canvas]");
  const toggle = document.querySelector("[data-molecule-toggle]");
  const viewButtons = [...document.querySelectorAll("[data-molecule-view]")];
  const modeCopy = document.querySelector(".molecule-mode-copy");
  const modeIndex = document.querySelector("[data-molecule-mode-index]");
  const modeTitle = document.querySelector("[data-molecule-mode-title]");
  const modeDescription = document.querySelector("[data-molecule-mode-description]");
  const identity = document.querySelector("[data-molecule-identity]");
  const subtitle = document.querySelector("[data-molecule-subtitle]");
  const status = document.querySelector("[data-molecule-status]");
  const readouts = Object.fromEntries(
    [...document.querySelectorAll("[data-molecule-readout]")].map((element) => [
      element.dataset.moleculeReadout,
      element,
    ]),
  );
  const context = canvas?.getContext("2d");

  if (!stage || !canvas || !context) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const colors = ["#62ecd8", "#75b7ff", "#c276ff", "#d8fff8"];
  const points = [];
  const edges = [];
  const ambient = [];
  const modes = {
    overview: {
      index: "VIEW 01 · STRUCTURE",
      title: "全分子结构视图",
      description: "拖动指针探索重链、轻链与铰链区域；选择视图，镜头将平滑聚焦到对应结构状态。",
      identity: "ANTIBODY STRUCTURE EXPLORER",
      subtitle: "Interactive molecular data model",
      readout: ["OVERVIEW", "FULL MOLECULE", "EXPLORING"],
      status: "INTERACTIVE CANVAS · POINTER READY",
      rotation: [-0.08, 0],
      scale: 1,
      offset: [0, 0],
    },
    paratope: {
      index: "VIEW 02 · PARATOPE",
      title: "双价结合位点聚焦",
      description: "镜头锁定 Fab 末端的互补决定区，展示两侧结合位点在抗原识别中的空间关系。",
      identity: "PARATOPE FOCUS",
      subtitle: "Dual binding-site geometry",
      readout: ["SITE FOCUS", "CDR REGIONS", "MAPPED"],
      status: "CAMERA LOCK · CDR SITES HIGHLIGHTED",
      rotation: [-0.17, -0.42],
      scale: 1.18,
      offset: [0, 0.22],
    },
    sequence: {
      index: "VIEW 03 · SEQUENCE",
      title: "序列—结构映射",
      description: "重链、轻链与 CDR-H3 片段以同一色彩语言映射到结构骨架，连接序列信息与空间位置。",
      identity: "SEQUENCE MAPPING",
      subtitle: "VH · VL · CDR regions",
      readout: ["SEQUENCE", "CHAIN DOMAINS", "CONNECTED"],
      status: "RESIDUE SIGNAL · STRUCTURE MAPPED",
      rotation: [-0.04, 0.55],
      scale: 1.06,
      offset: [0, 0.08],
    },
    binding: {
      index: "VIEW 04 · BINDING",
      title: "抗原接近与结合演示",
      description: "抗原沿识别路径接近 Fab 结合位点，形成稳定复合物，并实时呈现界面接触状态。",
      identity: "ANTIGEN BINDING",
      subtitle: "Recognition · approach · complex",
      readout: ["BINDING", "FAB INTERFACE", "COMPLEXED"],
      status: "ANTIGEN TRAJECTORY · INTERFACE ACTIVE",
      rotation: [-0.12, -0.18],
      scale: 1,
      offset: [0.05, 0.45],
    },
  };
  let width = 0;
  let height = 0;
  let pixelRatio = 1;
  const baseAngle = -0.28;
  let motionPhase = 0;
  let targetRotationX = -0.08;
  let targetRotationY = 0;
  let currentRotationX = -0.08;
  let currentRotationY = 0;
  let targetScale = 1;
  let currentScale = 1;
  let targetOffsetX = 0;
  let targetOffsetY = 0;
  let currentOffsetX = 0;
  let currentOffsetY = 0;
  let pointerOffsetX = 0;
  let pointerOffsetY = 0;
  let activeMode = "overview";
  let bindingProgress = 0;
  let isVisible = true;
  let isPaused = reducedMotion;
  let previousTime = performance.now();
  let lastRenderedTime = 0;
  let animationFrame;
  let modeCopyTimer;

  const interpolate = (start, end, progress) => ({
    x: start.x + (end.x - start.x) * progress,
    y: start.y + (end.y - start.y) * progress,
    z: start.z + (end.z - start.z) * progress,
  });

  const addChain = (start, end, count, color, phase = 0) => {
    const chain = [];

    for (let index = 0; index < count; index += 1) {
      const progress = index / (count - 1);
      const base = interpolate(start, end, progress);
      const taper = Math.sin(progress * Math.PI);
      const pointIndex = points.push({
        x: base.x + Math.sin(progress * Math.PI * 3 + phase) * 0.045 * taper,
        y: base.y,
        z: base.z + Math.cos(progress * Math.PI * 4 + phase) * 0.12 * taper,
        color,
        size: index % 4 === 0 ? 1.2 : 0.86,
      }) - 1;

      chain.push(pointIndex);
      if (index > 0) edges.push([chain[index - 1], pointIndex, color]);
    }

    return chain;
  };

  const connectChains = (first, second, color, interval = 5) => {
    const length = Math.min(first.length, second.length);
    for (let index = interval; index < length - 1; index += interval) {
      edges.push([first[index], second[index], color, 0.34]);
    }
  };

  const stemLeft = addChain(
    { x: -0.17, y: 1.48, z: 0 },
    { x: -0.15, y: 0.08, z: 0 },
    22,
    colors[0],
    0.2,
  );
  const stemRight = addChain(
    { x: 0.17, y: 1.48, z: 0 },
    { x: 0.15, y: 0.08, z: 0 },
    22,
    colors[1],
    1.6,
  );
  const leftHeavy = addChain(
    { x: -0.15, y: 0.08, z: 0 },
    { x: -1.42, y: -1.3, z: 0.06 },
    25,
    colors[0],
    0.8,
  );
  const rightHeavy = addChain(
    { x: 0.15, y: 0.08, z: 0 },
    { x: 1.42, y: -1.3, z: -0.06 },
    25,
    colors[1],
    2.1,
  );
  const leftLight = addChain(
    { x: -0.48, y: -0.16, z: 0.12 },
    { x: -1.58, y: -1.16, z: 0.18 },
    19,
    colors[2],
    2.8,
  );
  const rightLight = addChain(
    { x: 0.48, y: -0.16, z: -0.12 },
    { x: 1.58, y: -1.16, z: -0.18 },
    19,
    colors[3],
    4.2,
  );

  connectChains(stemLeft, stemRight, colors[3], 4);
  connectChains(leftHeavy.slice(6), leftLight, colors[2], 5);
  connectChains(rightHeavy.slice(6), rightLight, colors[3], 5);
  edges.push([stemLeft.at(-1), stemRight.at(-1), colors[3], 0.8]);

  const paratopePoints = new Set([
    ...leftHeavy.slice(-5),
    ...rightHeavy.slice(-5),
    ...leftLight.slice(-4),
    ...rightLight.slice(-4),
  ]);
  const heavyPoints = new Set([...stemLeft, ...stemRight, ...leftHeavy, ...rightHeavy]);
  const cdrPoints = new Set([...leftHeavy.slice(-7), ...rightHeavy.slice(-7)]);
  const antigenShape = [
    [-0.18, -0.12, 0.05],
    [0.02, -0.2, 0.12],
    [0.2, -0.08, -0.03],
    [-0.1, 0.08, -0.1],
    [0.12, 0.12, 0.08],
    [-0.24, 0.18, 0.02],
    [0.28, 0.16, 0.14],
    [0.04, 0.3, -0.08],
    [-0.04, -0.34, -0.04],
  ];

  let seed = 73421;
  const random = () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  for (let index = 0; index < 96; index += 1) {
    const radius = 1.5 + random() * 2.2;
    const theta = random() * Math.PI * 2;
    const phi = Math.acos(2 * random() - 1);
    ambient.push({
      x: radius * Math.sin(phi) * Math.cos(theta),
      y: radius * Math.cos(phi),
      z: radius * Math.sin(phi) * Math.sin(theta),
      size: 0.45 + random() * 1.2,
      alpha: 0.08 + random() * 0.26,
      color: colors[Math.floor(random() * colors.length)],
    });
  }

  const rotatePoint = (point, rotationX, rotationY) => {
    const cosY = Math.cos(rotationY);
    const sinY = Math.sin(rotationY);
    const xAfterY = point.x * cosY - point.z * sinY;
    const zAfterY = point.x * sinY + point.z * cosY;
    const cosX = Math.cos(rotationX);
    const sinX = Math.sin(rotationX);

    return {
      x: xAfterY,
      y: point.y * cosX - zAfterY * sinX,
      z: point.y * sinX + zAfterY * cosX,
    };
  };

  const projectPoint = (point) => {
    const camera = 5.2;
    const depth = Math.max(1.8, camera + point.z);
    const perspective = camera / depth;
    const scale = Math.min(width, height) * (width < 620 ? 0.23 : 0.225) * currentScale;

    return {
      x: width * 0.5 + (point.x + currentOffsetX) * scale * perspective,
      y: height * (width < 620 ? 0.4 : 0.42) + (point.y + currentOffsetY) * scale * perspective,
      z: point.z,
      perspective,
    };
  };

  const drawCallout = (point, title, detail, align = "left") => {
    const direction = align === "left" ? 1 : -1;
    const lineEndX = point.x + direction * 62;
    const textX = lineEndX + direction * 8;
    context.save();
    context.strokeStyle = "rgba(99, 243, 217, 0.62)";
    context.fillStyle = "rgba(223, 255, 249, 0.92)";
    context.lineWidth = 1;
    context.beginPath();
    context.arc(point.x, point.y, 12, 0, Math.PI * 2);
    context.moveTo(point.x + direction * 12, point.y);
    context.lineTo(lineEndX, point.y);
    context.stroke();
    context.textAlign = align;
    context.font = '600 10px "Segoe UI", sans-serif';
    context.fillText(title, textX, point.y - 4);
    context.fillStyle = "rgba(255, 255, 255, 0.44)";
    context.font = '500 8px "Segoe UI", sans-serif';
    context.fillText(detail, textX, point.y + 9);
    context.restore();
  };

  const draw = () => {
    if (!width || !height) return;

    context.clearRect(0, 0, width, height);
    const ambientRotation = isPaused || reducedMotion ? 0 : Math.sin(motionPhase) * 0.08;
    const rotationY = baseAngle + ambientRotation + currentRotationY;
    const transformed = points.map((point) => ({
      ...projectPoint(rotatePoint(point, currentRotationX, rotationY)),
      color: point.color,
      size: point.size,
    }));

    context.save();
    context.globalCompositeOperation = "lighter";
    ambient.slice(0, width < 620 ? 48 : ambient.length).forEach((particle) => {
      const rotated = rotatePoint(particle, currentRotationX * 0.35, rotationY * 0.28);
      const projected = projectPoint(rotated);
      const radius = particle.size * projected.perspective;
      context.beginPath();
      context.fillStyle = particle.color;
      context.globalAlpha = particle.alpha * (activeMode === "overview" ? 1 : 0.52);
      context.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
      context.fill();
    });
    context.restore();

    edges
      .map((edge) => ({
        edge,
        depth: (transformed[edge[0]].z + transformed[edge[1]].z) / 2,
      }))
      .sort((first, second) => first.depth - second.depth)
      .forEach(({ edge }) => {
        const [fromIndex, toIndex, color, opacity = 0.5] = edge;
        const from = transformed[fromIndex];
        const to = transformed[toIndex];
        const isFocused =
          activeMode === "overview" ||
          activeMode === "sequence" ||
          (activeMode === "paratope" &&
            (paratopePoints.has(fromIndex) || paratopePoints.has(toIndex))) ||
          (activeMode === "binding" &&
            (cdrPoints.has(fromIndex) || cdrPoints.has(toIndex)));
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.strokeStyle = color;
        context.globalAlpha =
          opacity * Math.min(from.perspective, to.perspective) * (isFocused ? 1 : 0.22);
        context.lineWidth = Math.max(0.6, (isFocused ? 1.3 : 0.8) * from.perspective);
        context.stroke();
      });

    transformed
      .map((point, index) => ({ ...point, index }))
      .sort((first, second) => first.z - second.z)
      .forEach((point) => {
        const isParatope = paratopePoints.has(point.index);
        const isCdr = cdrPoints.has(point.index);
        const isHeavy = heavyPoints.has(point.index);
        const isFocused =
          activeMode === "overview" ||
          activeMode === "sequence" ||
          (activeMode === "paratope" && isParatope) ||
          (activeMode === "binding" && isCdr);
        const sequencePulse =
          activeMode === "sequence"
            ? Math.max(0, Math.sin(point.index * 0.58 - motionPhase * 15)) * 1.25
            : 0;
        const radius = Math.max(
          1.6,
          (3.6 + sequencePulse) * point.size * point.perspective * (isFocused ? 1 : 0.72),
        );
        context.save();
        context.globalAlpha = Math.min(1, (isFocused ? 0.64 : 0.18) + point.perspective * 0.26);
        context.shadowBlur = radius * (isFocused ? 3.6 : 1.4);
        context.shadowColor =
          activeMode === "sequence" && isHeavy ? colors[0] : point.color;
        context.fillStyle =
          activeMode === "sequence" && isHeavy ? colors[0] : point.color;
        context.beginPath();
        context.arc(point.x, point.y, radius, 0, Math.PI * 2);
        context.fill();
        context.restore();
      });

    if (activeMode === "binding") {
      const easedBinding = 1 - (1 - bindingProgress) ** 3;
      const target = points[leftHeavy.at(-1)];
      const antigenCenter = interpolate(
        { x: -3.1, y: -0.6, z: 0.65 },
        { x: target.x - 0.22, y: target.y - 0.26, z: target.z + 0.08 },
        easedBinding,
      );
      const projectedCenter = projectPoint(
        rotatePoint(antigenCenter, currentRotationX, rotationY),
      );

      context.save();
      context.setLineDash([4, 8]);
      context.strokeStyle = "rgba(117, 183, 255, 0.38)";
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(projectedCenter.x - 76, projectedCenter.y - 32);
      context.lineTo(projectedCenter.x, projectedCenter.y);
      context.stroke();
      context.setLineDash([]);
      context.globalCompositeOperation = "lighter";
      antigenShape.forEach(([x, y, z], index) => {
        const projected = projectPoint(
          rotatePoint(
            {
              x: antigenCenter.x + x,
              y: antigenCenter.y + y,
              z: antigenCenter.z + z,
            },
            currentRotationX,
            rotationY,
          ),
        );
        const radius = (index % 3 === 0 ? 9 : 7) * projected.perspective;
        context.globalAlpha = 0.72;
        context.fillStyle = index % 2 ? "#75b7ff" : "#a642ff";
        context.shadowBlur = 18;
        context.shadowColor = context.fillStyle;
        context.beginPath();
        context.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
        context.fill();
      });
      context.restore();

    }

    const hinge = projectPoint(rotatePoint({ x: 0, y: 0.08, z: 0 }, currentRotationX, rotationY));
    const pulse = reducedMotion || isPaused ? 18 : 18 + Math.sin(performance.now() / 520) * 3;
    context.beginPath();
    context.globalAlpha = 0.2;
    context.strokeStyle = colors[0];
    context.lineWidth = 1;
    context.arc(hinge.x, hinge.y, pulse, 0, Math.PI * 2);
    context.stroke();
    context.globalAlpha = 1;

    if (activeMode === "paratope") {
      drawCallout(transformed[leftHeavy.at(-1)], "PARATOPE A", "CDR-H3 FOCUS", "left");
      drawCallout(transformed[rightHeavy.at(-1)], "PARATOPE B", "CDR-H3 FOCUS", "right");
    } else if (activeMode === "sequence") {
      drawCallout(transformed[leftHeavy.at(-4)], "CDR-H3", "ARGLYFDYW", "left");
    }
  };

  const resize = () => {
    const bounds = stage.getBoundingClientRect();
    width = Math.max(1, bounds.width);
    height = Math.max(1, bounds.height);
    pixelRatio = Math.min(window.devicePixelRatio || 1, width < 620 ? 1.5 : 2);
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    draw();
  };

  const updateToggle = () => {
    if (!toggle) return;
    toggle.setAttribute("aria-pressed", String(isPaused));
    toggle.textContent = reducedMotion ? "已减少动态" : isPaused ? "继续动态" : "暂停动态";
    toggle.disabled = reducedMotion;
  };

  const startAnimation = () => {
    if (animationFrame || !isVisible || document.hidden) return;
    previousTime = performance.now();
    animationFrame = window.requestAnimationFrame(animate);
  };

  function animate(time) {
    animationFrame = undefined;
    const frameInterval = width < 620 ? 1000 / 30 : 0;
    if (frameInterval && time - lastRenderedTime < frameInterval) {
      animationFrame = window.requestAnimationFrame(animate);
      return;
    }
    lastRenderedTime = time;
    const delta = Math.min(40, time - previousTime);
    previousTime = time;
    currentRotationX += (targetRotationX - currentRotationX) * 0.065;
    currentRotationY += (targetRotationY - currentRotationY) * 0.065;
    currentScale += (targetScale - currentScale) * 0.065;
    currentOffsetX += (targetOffsetX - currentOffsetX) * 0.065;
    currentOffsetY += (targetOffsetY - currentOffsetY) * 0.065;
    if (activeMode === "binding" && bindingProgress < 1) {
      bindingProgress = Math.min(1, bindingProgress + delta / 1250);
    }
    if (!isPaused) motionPhase += delta * 0.00032;

    draw();
    const isSettling =
      Math.abs(targetRotationX - currentRotationX) > 0.001 ||
      Math.abs(targetRotationY - currentRotationY) > 0.001 ||
      Math.abs(targetScale - currentScale) > 0.001 ||
      Math.abs(targetOffsetX - currentOffsetX) > 0.001 ||
      Math.abs(targetOffsetY - currentOffsetY) > 0.001 ||
      (activeMode === "binding" && bindingProgress < 1);

    if ((!isPaused || isSettling) && isVisible && !document.hidden) {
      animationFrame = window.requestAnimationFrame(animate);
    }
  }

  const setMode = (modeName) => {
    const mode = modes[modeName];
    if (!mode) return;

    activeMode = modeName;
    stage.dataset.moleculeMode = modeName;
    pointerOffsetX = 0;
    pointerOffsetY = 0;
    [targetRotationX, targetRotationY] = mode.rotation;
    targetScale = mode.scale;
    [targetOffsetX, targetOffsetY] = mode.offset;
    bindingProgress = modeName === "binding" ? 0 : 1;

    viewButtons.forEach((button) => {
      const isActive = button.dataset.moleculeView === modeName;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });

    if (modeIndex) modeIndex.textContent = mode.index;
    if (modeTitle) modeTitle.textContent = mode.title;
    if (modeDescription) modeDescription.textContent = mode.description;
    if (identity) identity.textContent = mode.identity;
    if (subtitle) subtitle.textContent = mode.subtitle;
    if (status) status.textContent = mode.status;
    if (readouts.view) readouts.view.textContent = mode.readout[0];
    if (readouts.focus) readouts.focus.textContent = mode.readout[1];
    if (readouts.state) readouts.state.textContent = mode.readout[2];
    canvas.setAttribute(
      "aria-label",
      `交互式抗体结构演示：${mode.title}。${mode.description}`,
    );

    modeCopy?.classList.add("is-changing");
    window.clearTimeout(modeCopyTimer);
    modeCopyTimer = window.setTimeout(() => modeCopy?.classList.remove("is-changing"), 280);

    if (reducedMotion) {
      currentRotationX = targetRotationX;
      currentRotationY = targetRotationY;
      currentScale = targetScale;
      currentOffsetX = targetOffsetX;
      currentOffsetY = targetOffsetY;
      bindingProgress = 1;
      draw();
      return;
    }

    startAnimation();
  };

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.moleculeView));
  });

  stage.addEventListener("pointermove", (event) => {
    if (event.pointerType === "touch") return;
    if (event.target.closest?.(".molecule-console, .molecule-stage-footer")) return;
    const bounds = stage.getBoundingClientRect();
    const horizontal = (event.clientX - bounds.left) / bounds.width - 0.5;
    const vertical = (event.clientY - bounds.top) / bounds.height - 0.5;
    pointerOffsetX = vertical * 0.12;
    pointerOffsetY = horizontal * 0.28;
    targetRotationX = modes[activeMode].rotation[0] + pointerOffsetX;
    targetRotationY = modes[activeMode].rotation[1] + pointerOffsetY;
    startAnimation();
  });

  stage.addEventListener("pointerleave", () => {
    pointerOffsetX = 0;
    pointerOffsetY = 0;
    targetRotationX = modes[activeMode].rotation[0];
    targetRotationY = modes[activeMode].rotation[1];
    startAnimation();
  });

  toggle?.addEventListener("click", () => {
    if (reducedMotion) return;
    isPaused = !isPaused;
    updateToggle();
    draw();
    startAnimation();
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisible = entry.isIntersecting;
        if (isVisible) {
          draw();
          startAnimation();
        }
      },
      { rootMargin: "20% 0px", threshold: 0.02 },
    );
    observer.observe(stage);
  }

  if ("ResizeObserver" in window) {
    new ResizeObserver(resize).observe(stage);
  } else {
    window.addEventListener("resize", resize);
  }

  document.addEventListener("visibilitychange", startAnimation);
  updateToggle();
  resize();
  startAnimation();
})();
