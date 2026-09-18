(() => {
  const stage = document.querySelector("[data-molecule-stage]");
  const canvas = document.querySelector("[data-molecule-canvas]");
  const toggle = document.querySelector("[data-molecule-toggle]");
  const context = canvas?.getContext("2d");

  if (!stage || !canvas || !context) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const colors = ["#62ecd8", "#75b7ff", "#c276ff", "#d8fff8"];
  const points = [];
  const edges = [];
  const ambient = [];
  let width = 0;
  let height = 0;
  let pixelRatio = 1;
  const baseAngle = -0.28;
  let motionPhase = 0;
  let targetRotationX = -0.08;
  let targetRotationY = 0;
  let currentRotationX = -0.08;
  let currentRotationY = 0;
  let isVisible = true;
  let isPaused = reducedMotion;
  let previousTime = performance.now();
  let lastRenderedTime = 0;
  let animationFrame;

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
    const scale = Math.min(width, height) * (width < 620 ? 0.255 : 0.235);

    return {
      x: width * 0.5 + point.x * scale * perspective,
      y: height * 0.51 + point.y * scale * perspective,
      z: point.z,
      perspective,
    };
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
      context.globalAlpha = particle.alpha;
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
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.strokeStyle = color;
        context.globalAlpha = opacity * Math.min(from.perspective, to.perspective);
        context.lineWidth = Math.max(0.6, 1.15 * from.perspective);
        context.stroke();
      });

    transformed
      .map((point, index) => ({ ...point, index }))
      .sort((first, second) => first.z - second.z)
      .forEach((point) => {
        const radius = Math.max(1.8, 3.6 * point.size * point.perspective);
        context.save();
        context.globalAlpha = Math.min(1, 0.62 + point.perspective * 0.28);
        context.shadowBlur = radius * 3.2;
        context.shadowColor = point.color;
        context.fillStyle = point.color;
        context.beginPath();
        context.arc(point.x, point.y, radius, 0, Math.PI * 2);
        context.fill();
        context.restore();
      });

    const hinge = projectPoint(rotatePoint({ x: 0, y: 0.08, z: 0 }, currentRotationX, rotationY));
    const pulse = reducedMotion || isPaused ? 18 : 18 + Math.sin(performance.now() / 520) * 3;
    context.beginPath();
    context.globalAlpha = 0.2;
    context.strokeStyle = colors[0];
    context.lineWidth = 1;
    context.arc(hinge.x, hinge.y, pulse, 0, Math.PI * 2);
    context.stroke();
    context.globalAlpha = 1;
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
    if (animationFrame || isPaused || !isVisible || document.hidden) return;
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
    currentRotationX += (targetRotationX - currentRotationX) * 0.045;
    currentRotationY += (targetRotationY - currentRotationY) * 0.045;

    if (!isPaused && isVisible && !document.hidden) {
      motionPhase += delta * 0.00032;
      draw();
      animationFrame = window.requestAnimationFrame(animate);
    }
  }

  stage.addEventListener("pointermove", (event) => {
    if (event.pointerType === "touch") return;
    const bounds = stage.getBoundingClientRect();
    const horizontal = (event.clientX - bounds.left) / bounds.width - 0.5;
    const vertical = (event.clientY - bounds.top) / bounds.height - 0.5;
    targetRotationY = horizontal * 0.48;
    targetRotationX = -0.08 + vertical * 0.18;
    if (isPaused) draw();
  });

  stage.addEventListener("pointerleave", () => {
    targetRotationY = 0;
    targetRotationX = -0.08;
    if (isPaused) draw();
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
