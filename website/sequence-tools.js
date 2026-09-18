(() => {
  const aminoAcidMass = {
    A: 71.0788,
    C: 103.1388,
    D: 115.0886,
    E: 129.1155,
    F: 147.1766,
    G: 57.0519,
    H: 137.1411,
    I: 113.1594,
    K: 128.1741,
    L: 113.1594,
    M: 131.1926,
    N: 114.1038,
    P: 97.1167,
    Q: 128.1307,
    R: 156.1875,
    S: 87.0782,
    T: 101.1051,
    V: 99.1326,
    W: 186.2132,
    Y: 163.176,
  };

  const hydropathy = {
    A: 1.8,
    C: 2.5,
    D: -3.5,
    E: -3.5,
    F: 2.8,
    G: -0.4,
    H: -3.2,
    I: 4.5,
    K: -3.9,
    L: 3.8,
    M: 1.9,
    N: -3.5,
    P: -1.6,
    Q: -3.5,
    R: -4.5,
    S: -0.8,
    T: -0.7,
    V: 4.2,
    W: -0.9,
    Y: -1.3,
  };

  const codonTable = {
    TTT: "F",
    TTC: "F",
    TTA: "L",
    TTG: "L",
    TCT: "S",
    TCC: "S",
    TCA: "S",
    TCG: "S",
    TAT: "Y",
    TAC: "Y",
    TAA: "*",
    TAG: "*",
    TGT: "C",
    TGC: "C",
    TGA: "*",
    TGG: "W",
    CTT: "L",
    CTC: "L",
    CTA: "L",
    CTG: "L",
    CCT: "P",
    CCC: "P",
    CCA: "P",
    CCG: "P",
    CAT: "H",
    CAC: "H",
    CAA: "Q",
    CAG: "Q",
    CGT: "R",
    CGC: "R",
    CGA: "R",
    CGG: "R",
    ATT: "I",
    ATC: "I",
    ATA: "I",
    ATG: "M",
    ACT: "T",
    ACC: "T",
    ACA: "T",
    ACG: "T",
    AAT: "N",
    AAC: "N",
    AAA: "K",
    AAG: "K",
    AGT: "S",
    AGC: "S",
    AGA: "R",
    AGG: "R",
    GTT: "V",
    GTC: "V",
    GTA: "V",
    GTG: "V",
    GCT: "A",
    GCC: "A",
    GCA: "A",
    GCG: "A",
    GAT: "D",
    GAC: "D",
    GAA: "E",
    GAG: "E",
    GGT: "G",
    GGC: "G",
    GGA: "G",
    GGG: "G",
  };

  const iupacBases = {
    A: "A",
    C: "C",
    G: "G",
    T: "T",
    R: "AG",
    Y: "CT",
    S: "CG",
    W: "AT",
    K: "GT",
    M: "AC",
    B: "CGT",
    D: "AGT",
    H: "ACT",
    V: "ACG",
    N: "ACGT",
  };

  const dnaComplements = {
    A: "T",
    T: "A",
    C: "G",
    G: "C",
    R: "Y",
    Y: "R",
    S: "S",
    W: "W",
    K: "M",
    M: "K",
    B: "V",
    V: "B",
    D: "H",
    H: "D",
    N: "N",
  };

  const nTerminalPka = { A: 7.59, M: 7, S: 6.93, P: 8.36, T: 6.82, V: 7.44, E: 7.7 };
  const cTerminalPka = { D: 4.55, E: 4.75 };

  const cleanSequence = (rawSequence) =>
    String(rawSequence ?? "")
      .split(/\r?\n/)
      .filter((line) => !line.trim().startsWith(">"))
      .join("")
      .replace(/[\s\d.-]/g, "")
      .toUpperCase();

  const ensureSingleFastaRecord = (rawSequence) => {
    const records = String(rawSequence ?? "")
      .split(/\r?\n/)
      .filter((line) => line.trim().startsWith(">")).length;
    if (records > 1) throw new Error("当前一次仅分析一条 FASTA 记录。");
  };

  const countResidues = (sequence) =>
    [...sequence].reduce((counts, residue) => {
      counts[residue] = (counts[residue] ?? 0) + 1;
      return counts;
    }, {});

  const formatSequence = (sequence, limit = 2400) => {
    const visible = sequence.slice(0, limit);
    const wrapped = visible.match(/.{1,80}/g)?.join("\n") ?? "";
    return sequence.length > limit
      ? `${wrapped}\n… 已截断显示；完整长度 ${sequence.length.toLocaleString()}`
      : wrapped;
  };

  const invalidCharacters = (sequence, validCharacters) =>
    [...sequence]
      .map((character, index) => ({ character, position: index + 1 }))
      .filter(({ character }) => !validCharacters.includes(character));

  const calculateProteinCharge = (counts, sequence, ph) => {
    const positiveTerminal =
      1 / (1 + 10 ** (ph - (nTerminalPka[sequence[0]] ?? 7.5)));
    const negativeTerminal =
      1 / (1 + 10 ** ((cTerminalPka[sequence.at(-1)] ?? 3.55) - ph));
    const positiveSideChains =
      (counts.K ?? 0) / (1 + 10 ** (ph - 10)) +
      (counts.R ?? 0) / (1 + 10 ** (ph - 12)) +
      (counts.H ?? 0) / (1 + 10 ** (ph - 5.98));
    const negativeSideChains =
      (counts.D ?? 0) / (1 + 10 ** (4.05 - ph)) +
      (counts.E ?? 0) / (1 + 10 ** (4.45 - ph)) +
      (counts.C ?? 0) / (1 + 10 ** (9 - ph)) +
      (counts.Y ?? 0) / (1 + 10 ** (10 - ph));

    return positiveTerminal + positiveSideChains - negativeTerminal - negativeSideChains;
  };

  const calculateIsoelectricPoint = (counts, sequence) => {
    let lower = 0;
    let upper = 14;

    for (let iteration = 0; iteration < 80; iteration += 1) {
      const midpoint = (lower + upper) / 2;
      if (calculateProteinCharge(counts, sequence, midpoint) > 0) lower = midpoint;
      else upper = midpoint;
    }

    return (lower + upper) / 2;
  };

  const analyzeProtein = (rawSequence) => {
    ensureSingleFastaRecord(rawSequence);
    const sequence = cleanSequence(rawSequence);
    if (!sequence) throw new Error("请输入蛋白质或抗体序列。");
    if (sequence.length > 100000) throw new Error("蛋白质序列请控制在 100,000 aa 以内。");

    const invalid = invalidCharacters(sequence, Object.keys(aminoAcidMass));
    if (invalid.length) {
      const locations = invalid
        .slice(0, 5)
        .map(({ character, position }) => `${character}（位置 ${position}）`)
        .join("、");
      throw new Error(`检测到非标准氨基酸字符：${locations}`);
    }

    const counts = countResidues(sequence);
    const molecularWeight =
      [...sequence].reduce((total, residue) => total + aminoAcidMass[residue], 0) + 18.01524;
    const gravy =
      [...sequence].reduce((total, residue) => total + hydropathy[residue], 0) / sequence.length;
    const extinctionReduced = (counts.W ?? 0) * 5500 + (counts.Y ?? 0) * 1490;
    const extinctionOxidized = extinctionReduced + Math.floor((counts.C ?? 0) / 2) * 125;
    const charged = "DEKRH".split("").reduce((total, residue) => total + (counts[residue] ?? 0), 0);
    const polar = "STNQCY".split("").reduce((total, residue) => total + (counts[residue] ?? 0), 0);
    const aromatic = "FWY".split("").reduce((total, residue) => total + (counts[residue] ?? 0), 0);

    return {
      sequence,
      length: sequence.length,
      molecularWeight,
      isoelectricPoint: calculateIsoelectricPoint(counts, sequence),
      gravy,
      extinction: extinctionOxidized,
      extinctionReduced,
      extinctionOxidized,
      counts,
      summary: [
        `带电残基（D/E/K/R/H）  ${charged} · ${((charged / sequence.length) * 100).toFixed(1)}%`,
        `极性残基（S/T/N/Q/C/Y） ${polar} · ${((polar / sequence.length) * 100).toFixed(1)}%`,
        `芳香残基（F/W/Y）      ${aromatic} · ${((aromatic / sequence.length) * 100).toFixed(1)}%`,
        `Cys / Trp / Tyr          ${counts.C ?? 0} / ${counts.W ?? 0} / ${counts.Y ?? 0}`,
        "",
        `ε280 还原态 / 最大氧化态  ${extinctionReduced.toLocaleString()} / ${extinctionOxidized.toLocaleString()} M⁻¹cm⁻¹`,
        "分子量按平均残基质量加一分子水估算，不计二硫键失氢与翻译后修饰；",
        "pI 使用 Bjellqvist 参数集；重链、轻链及其他多肽链应分别计算。",
      ].join("\n"),
    };
  };

  const reverseComplement = (sequence) => {
    return [...sequence]
      .reverse()
      .map((base) => dnaComplements[base])
      .join("");
  };

  const translateCodon = (codon) => {
    let expanded = [""];
    [...codon].forEach((base) => {
      expanded = expanded.flatMap((prefix) => [...iupacBases[base]].map((value) => prefix + value));
    });
    const products = new Set(expanded.map((value) => codonTable[value]));
    return products.size === 1 ? [...products][0] : "X";
  };

  const translateDna = (sequence) => {
    let protein = "";
    for (let index = 0; index <= sequence.length - 3; index += 3) {
      const codon = sequence.slice(index, index + 3);
      protein += translateCodon(codon);
    }
    return protein;
  };

  const analyzeDna = (rawSequence) => {
    ensureSingleFastaRecord(rawSequence);
    const sequence = cleanSequence(rawSequence).replaceAll("U", "T");
    if (!sequence) throw new Error("请输入 DNA 序列。");
    if (sequence.length > 300000) throw new Error("DNA 序列请控制在 300,000 nt 以内。");

    const invalid = invalidCharacters(sequence, Object.keys(iupacBases));
    if (invalid.length) {
      const locations = invalid
        .slice(0, 5)
        .map(({ character, position }) => `${character}（位置 ${position}）`)
        .join("、");
      throw new Error(`检测到非 DNA 字符：${locations}`);
    }

    const counts = countResidues(sequence);
    const canonicalLength =
      (counts.A ?? 0) + (counts.C ?? 0) + (counts.G ?? 0) + (counts.T ?? 0);

    const ambiguousBases = sequence.length - canonicalLength;
    const gcCount = (counts.G ?? 0) + (counts.C ?? 0);
    const gcPercent = ambiguousBases ? null : (gcCount / sequence.length) * 100;
    const atCount = (counts.A ?? 0) + (counts.T ?? 0);
    const meltingTemperature = ambiguousBases ? null : atCount * 2 + gcCount * 4;
    const complement = reverseComplement(sequence);
    const translation = translateDna(sequence);
    const untranslatedBases = sequence.length % 3;
    const warnings = [];
    if (ambiguousBases) warnings.push("含 IUPAC 模糊碱基，GC 与 Tm 不给出单一数值。");
    if (!ambiguousBases && (sequence.length < 14 || sequence.length > 20)) {
      warnings.push("Wallace Tm 主要适用于约 14–20 nt 的完全匹配短寡核苷酸。");
    }
    if (untranslatedBases) warnings.push(`末尾 ${untranslatedBases} nt 未进入阅读框 1 翻译。`);

    return {
      sequence,
      length: sequence.length,
      canonicalLength,
      gcPercent,
      meltingTemperature,
      complement,
      translation,
      ambiguousBases,
      untranslatedBases,
      warnings,
      summary: [
        ">reverse_complement_5to3",
        formatSequence(complement),
        "",
        ">translation_frame_1_standard_code",
        formatSequence(translation) || "(没有完整密码子)",
        "",
        `A / C / G / T / ambiguous  ${counts.A ?? 0} / ${counts.C ?? 0} / ${counts.G ?? 0} / ${counts.T ?? 0} / ${ambiguousBases}`,
        "",
        "粗略 Tm 使用 Wallace 规则：2 × (A+T) + 4 × (G+C)。",
        ...warnings.map((warning) => `注意：${warning}`),
      ].join("\n"),
    };
  };

  const api = { analyzeDna, analyzeProtein, cleanSequence, reverseComplement, translateDna };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;

  const lab = document.querySelector("[data-sequence-lab]");
  if (!lab) return;

  const modeButtons = [...lab.querySelectorAll("[data-sequence-mode]")];
  const input = lab.querySelector("[data-sequence-input]");
  const counter = lab.querySelector("[data-sequence-counter]");
  const feedback = lab.querySelector("[data-sequence-feedback]");
  const runButton = lab.querySelector("[data-sequence-run]");
  const clearButton = lab.querySelector("[data-sequence-clear]");
  const exampleButton = lab.querySelector("[data-sequence-example]");
  const copyButton = lab.querySelector("[data-sequence-copy]");
  const resultKind = lab.querySelector("[data-result-kind]");
  const outputTitle = lab.querySelector("[data-output-title]");
  const output = lab.querySelector("[data-sequence-output]");
  const resultSurface = lab.querySelector(".lab-results-panel");
  const metricLabels = [...lab.querySelectorAll("[data-metric-label]")];
  const metricValues = [...lab.querySelectorAll("[data-metric-value]")];
  const metricUnits = [...lab.querySelectorAll("[data-metric-unit]")];
  let mode = "protein";
  let latestSummary = "";

  const examples = {
    protein:
      "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS",
    dna: "ATGGCCTACGTTAACTGA",
  };

  const modeConfig = {
    protein: {
      kind: "PROTEIN",
      unit: "aa",
      placeholder: "直接粘贴氨基酸序列即可，无需添加 > 标题…",
      hint: "直接粘贴序列即可；空格、换行、行号与 FASTA 标题会自动清理。",
      outputTitle: "组成概览",
      labels: [
        "序列长度",
        "近似分子量",
        "理论等电点",
        "平均疏水性",
        "280 nm 最大氧化态",
      ],
      units: ["aa", "kDa", "pI", "GRAVY", "M⁻¹cm⁻¹"],
    },
    dna: {
      kind: "DNA",
      unit: "nt",
      placeholder: "直接粘贴 DNA 序列即可；U 将按 T 处理…",
      hint: "无需 FASTA 标题；支持 IUPAC DNA 代码，U 将按界面约定转换为 T。",
      outputTitle: "反向互补与阅读框 1",
      labels: ["序列长度", "GC 含量", "粗略 Tm", "阅读框 1", "模糊位点"],
      units: ["nt", "%", "°C", "aa", "nt"],
    },
  };

  const setFeedback = (message, isError = false) => {
    feedback.textContent = message;
    feedback.classList.toggle("error", isError);
  };

  const updateCounter = () => {
    counter.textContent = `${cleanSequence(input.value).length.toLocaleString()} ${modeConfig[mode].unit}`;
  };

  const resetResults = () => {
    metricValues.forEach((value) => {
      value.textContent = "—";
    });
    latestSummary = "";
    output.textContent = "输入序列后将在这里显示摘要。";
  };

  const setMode = (nextMode) => {
    mode = nextMode;
    const config = modeConfig[mode];
    modeButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.sequenceMode === mode));
    });
    metricLabels.forEach((label, index) => {
      label.textContent = config.labels[index];
    });
    metricUnits.forEach((unit, index) => {
      unit.textContent = config.units[index];
    });
    resultKind.textContent = config.kind;
    outputTitle.textContent = config.outputTitle;
    input.placeholder = config.placeholder;
    input.value = "";
    setFeedback(config.hint);
    updateCounter();
    resetResults();
  };

  const showResults = () => {
    try {
      if (mode === "protein") {
        const result = analyzeProtein(input.value);
        const values = [
          result.length.toLocaleString(),
          (result.molecularWeight / 1000).toFixed(2),
          result.isoelectricPoint.toFixed(2),
          result.gravy.toFixed(2),
          result.extinction.toLocaleString(),
        ];
        metricValues.forEach((value, index) => {
          value.textContent = values[index];
        });
        latestSummary = result.summary;
        setFeedback(`已完成 ${result.length.toLocaleString()} aa 的本地计算。`);
      } else {
        const result = analyzeDna(input.value);
        const values = [
          result.length.toLocaleString(),
          result.gcPercent === null ? "—" : result.gcPercent.toFixed(1),
          result.meltingTemperature === null ? "—" : result.meltingTemperature.toFixed(1),
          result.translation.length.toLocaleString(),
          result.ambiguousBases.toLocaleString(),
        ];
        metricValues.forEach((value, index) => {
          value.textContent = values[index];
        });
        latestSummary = result.summary;
        const warning = result.warnings[0] ? ` ${result.warnings[0]}` : "";
        setFeedback(`已完成 ${result.length.toLocaleString()} nt 的本地计算。${warning}`);
      }

      output.textContent = latestSummary;
    } catch (error) {
      resetResults();
      setFeedback(error.message, true);
    }
  };

  const runAnalysis = async () => {
    if (runButton.dataset.running === "true") return;
    const originalContent = runButton.innerHTML;
    runButton.dataset.running = "true";
    runButton.disabled = true;
    runButton.setAttribute("aria-busy", "true");
    runButton.classList.add("is-running");
    runButton.replaceChildren();
    const spinner = document.createElement("span");
    spinner.className = "button-spinner";
    spinner.setAttribute("aria-hidden", "true");
    runButton.append(spinner, document.createTextNode("计算中…"));
    resultSurface?.classList.add("is-calculating");

    try {
      await new Promise((resolve) => window.setTimeout(resolve, 420));
      showResults();
      resultSurface?.classList.remove("results-ready");
      if (resultSurface) void resultSurface.offsetWidth;
      resultSurface?.classList.add("results-ready");
      window.setTimeout(() => resultSurface?.classList.remove("results-ready"), 720);
    } finally {
      resultSurface?.classList.remove("is-calculating");
      runButton.innerHTML = originalContent;
      runButton.disabled = false;
      runButton.removeAttribute("aria-busy");
      runButton.classList.remove("is-running");
      delete runButton.dataset.running;
    }
  };

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.sequenceMode));
  });

  input.addEventListener("input", updateCounter);
  input.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runButton.click();
  });
  runButton.addEventListener("click", runAnalysis);
  clearButton.addEventListener("click", () => {
    input.value = "";
    input.focus();
    setFeedback(modeConfig[mode].hint);
    updateCounter();
    resetResults();
  });
  exampleButton.addEventListener("click", () => {
    input.value = examples[mode];
    updateCounter();
    resetResults();
    setFeedback("已载入示例序列；点击“开始计算”后显示结果。");
  });
  copyButton.addEventListener("click", async () => {
    if (!latestSummary) {
      setFeedback("请先完成一次计算。", true);
      return;
    }

    try {
      await navigator.clipboard.writeText(latestSummary);
      setFeedback("结果已复制到剪贴板。");
    } catch {
      setFeedback("浏览器未允许复制，请手动选择结果文本。", true);
    }
  });

  setMode("protein");
})();
