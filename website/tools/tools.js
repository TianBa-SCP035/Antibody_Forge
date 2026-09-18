(() => {
  const DNA_ALPHABET = "ACGUTRYSWKMBDHVN";
  const PROTEIN_ALPHABET = "ACDEFGHIKLMNPQRSTVWYBXZJUO";

  const normalizeSequenceText = (value) =>
    String(value ?? "")
      .replace(/[\s\d.-]/g, "")
      .toUpperCase();

  const cleanRawSequence = (raw) =>
    normalizeSequenceText(
      String(raw ?? "")
        .split(/\r?\n/)
        .filter((line) => !line.trim().startsWith(">"))
        .join(""),
    );

  const inferSequenceType = (sequence) => {
    if (!sequence) return "empty";
    if ([...sequence].every((character) => DNA_ALPHABET.includes(character))) return "DNA";
    if ([...sequence].every((character) => PROTEIN_ALPHABET.includes(character))) return "Protein";
    return "Invalid";
  };

  const parseFasta = (raw) => {
    const lines = String(raw ?? "").replace(/\r\n?/g, "\n").split("\n");
    const populatedLines = lines.map((line) => line.trim()).filter(Boolean);
    const hasFastaHeaders = populatedLines.some((line) => line.startsWith(">"));

    if (!hasFastaHeaders) {
      if (!populatedLines.length) throw new Error("请输入至少一条序列。");
      return populatedLines.map((line, index) => {
        const sequence = normalizeSequenceText(line);
        if (!sequence) throw new Error(`第 ${index + 1} 行没有可识别的序列字符。`);
        return {
          id: `sequence_${index + 1}`,
          sequence,
          length: sequence.length,
          type: inferSequenceType(sequence),
        };
      });
    }

    const records = [];
    let current;

    lines.forEach((line, lineIndex) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      if (trimmed.startsWith(">")) {
        if (current) records.push(current);
        current = {
          id: trimmed.slice(1).trim() || `sequence_${records.length + 1}`,
          sequenceParts: [],
          headerLine: lineIndex + 1,
        };
        return;
      }

      if (!current) {
        throw new Error(`第 ${lineIndex + 1} 行出现在 FASTA 标题之前。`);
      }
      current.sequenceParts.push(trimmed);
    });

    if (current) records.push(current);
    if (!records.length) throw new Error("未检测到 FASTA 记录；每条记录需要以 > 标题开始。");

    return records.map((record) => {
      const sequence = normalizeSequenceText(record.sequenceParts.join(""));
      if (!sequence) throw new Error(`记录 ${record.id} 没有序列内容。`);
      return {
        id: record.id,
        sequence,
        length: sequence.length,
        type: inferSequenceType(sequence),
      };
    });
  };

  const deduplicateFasta = (records) => {
    const seen = new Map();
    const unique = [];
    const annotated = records.map((record) => {
      if (record.type === "Invalid") return { ...record, status: "非法字符" };
      const first = seen.get(record.sequence);
      if (first) return { ...record, status: `重复于 ${first}` };
      seen.set(record.sequence, record.id);
      unique.push(record);
      return { ...record, status: "保留" };
    });
    return { annotated, unique };
  };

  const needlemanWunsch = (first, second, scoring = { match: 2, mismatch: -1, gap: -2 }) => {
    const sequenceA = cleanRawSequence(first);
    const sequenceB = cleanRawSequence(second);
    if (!sequenceA || !sequenceB) throw new Error("请输入两条需要比较的序列。");
    if (sequenceA.length > 2000 || sequenceB.length > 2000) {
      throw new Error("双序列全局比对请将每条序列控制在 2,000 个字符以内。");
    }

    const typeA = inferSequenceType(sequenceA);
    const typeB = inferSequenceType(sequenceB);
    if (typeA === "Invalid" || typeB === "Invalid") {
      throw new Error("序列包含不支持的字符；请输入标准蛋白字母或 IUPAC DNA 代码。");
    }

    const rows = sequenceA.length + 1;
    const columns = sequenceB.length + 1;
    const trace = Array.from({ length: rows }, () => new Uint8Array(columns));
    let previous = new Int32Array(columns);
    let current = new Int32Array(columns);

    for (let column = 1; column < columns; column += 1) {
      previous[column] = previous[column - 1] + scoring.gap;
      trace[0][column] = 3;
    }

    for (let row = 1; row < rows; row += 1) {
      current[0] = previous[0] + scoring.gap;
      trace[row][0] = 2;

      for (let column = 1; column < columns; column += 1) {
        const diagonal =
          previous[column - 1] +
          (sequenceA[row - 1] === sequenceB[column - 1] ? scoring.match : scoring.mismatch);
        const up = previous[column] + scoring.gap;
        const left = current[column - 1] + scoring.gap;

        if (diagonal >= up && diagonal >= left) {
          current[column] = diagonal;
          trace[row][column] = 1;
        } else if (up >= left) {
          current[column] = up;
          trace[row][column] = 2;
        } else {
          current[column] = left;
          trace[row][column] = 3;
        }
      }

      [previous, current] = [current, previous];
    }

    let row = sequenceA.length;
    let column = sequenceB.length;
    const alignedA = [];
    const alignedB = [];

    while (row > 0 || column > 0) {
      const direction = trace[row][column];
      if (direction === 1) {
        alignedA.push(sequenceA[row - 1]);
        alignedB.push(sequenceB[column - 1]);
        row -= 1;
        column -= 1;
      } else if (direction === 2) {
        alignedA.push(sequenceA[row - 1]);
        alignedB.push("-");
        row -= 1;
      } else {
        alignedA.push("-");
        alignedB.push(sequenceB[column - 1]);
        column -= 1;
      }
    }

    alignedA.reverse();
    alignedB.reverse();
    const outputA = alignedA.join("");
    const outputB = alignedB.join("");
    let matches = 0;
    let gaps = 0;
    const markers = [];

    for (let index = 0; index < outputA.length; index += 1) {
      if (outputA[index] === "-" || outputB[index] === "-") {
        gaps += 1;
        markers.push(" ");
      } else if (outputA[index] === outputB[index]) {
        matches += 1;
        markers.push("|");
      } else {
        markers.push("·");
      }
    }

    return {
      sequenceA,
      sequenceB,
      typeA,
      typeB,
      alignedA: outputA,
      alignedB: outputB,
      markers: markers.join(""),
      length: outputA.length,
      matches,
      gaps,
      identity: (matches / outputA.length) * 100,
      score: previous[sequenceB.length],
    };
  };

  const findOverlappingMotifs = (sequence, pattern, category, interpretation) => {
    const results = [];
    const expression = new RegExp(`(?=(${pattern}))`, "g");
    let match;
    while ((match = expression.exec(sequence))) {
      results.push({
        category,
        position: match.index + 1,
        motif: match[1],
        interpretation,
      });
      expression.lastIndex = match.index + 1;
    }
    return results;
  };

  const scanLiabilities = (raw) => {
    const sequence = cleanRawSequence(raw);
    if (!sequence) throw new Error("请输入蛋白质或抗体序列。");
    if (sequence.length > 100000) throw new Error("序列请控制在 100,000 aa 以内。");
    const invalid = [...sequence]
      .map((character, index) => ({ character, position: index + 1 }))
      .filter(({ character }) => !PROTEIN_ALPHABET.includes(character));
    if (invalid.length) {
      const first = invalid[0];
      throw new Error(`检测到非标准氨基酸 ${first.character}（位置 ${first.position}）。`);
    }

    const flags = [
      ...findOverlappingMotifs(
        sequence,
        "N[^P][ST]",
        "糖基化基序",
        "N-X-S/T（X≠P）是潜在 N-糖基化 sequon，是否修饰取决于结构与表达系统。",
      ),
      ...findOverlappingMotifs(
        sequence,
        "N[GST]",
        "脱酰胺提示",
        "该 Asn 邻域是脱酰胺复核重点，反应速率可结合结构暴露度与工艺条件评估。",
      ),
      ...findOverlappingMotifs(
        sequence,
        "D[GSTDH]",
        "异构化提示",
        "该 Asp 邻域建议结合结构暴露度、pH 和稳定性实验进一步复核。",
      ),
    ];

    ["M", "W"].forEach((residue) => {
      const positions = [...sequence]
        .map((character, index) => (character === residue ? index + 1 : null))
        .filter(Boolean);
      if (positions.length) {
        flags.push({
          category: "氧化敏感残基",
          position: positions.join(", "),
          motif: residue,
          interpretation: `${residue} 残基为氧化敏感位点，可结合溶剂暴露、制剂和应力条件评估。`,
        });
      }
    });

    const cysteinePositions = [...sequence]
      .map((character, index) => (character === "C" ? index + 1 : null))
      .filter(Boolean);
    if (cysteinePositions.length % 2 === 1) {
      flags.push({
        category: "Cys 配对提示",
        position: cysteinePositions.join(", "),
        motif: `${cysteinePositions.length} Cys`,
        interpretation: "Cys 总数为奇数，建议优先核对链边界、游离巯基与二硫键配对。",
      });
    }

    if (["Q", "E"].includes(sequence[0])) {
      flags.push({
        category: "N 端提示",
        position: 1,
        motif: sequence[0],
        interpretation: "N 端 Gln/Glu 可能形成焦谷氨酸，程度取决于序列环境与工艺条件。",
      });
    }

    if (sequence.at(-1) === "K") {
      flags.push({
        category: "C 端提示",
        position: sequence.length,
        motif: "K",
        interpretation: "C 端 Lys 常需结合宿主细胞加工和产品异质性数据进行评估。",
      });
    }

    return { sequence, flags };
  };

  const DNA_COMPLEMENT = {
    A: "T", C: "G", G: "C", T: "A", U: "A", R: "Y", Y: "R", S: "S",
    W: "W", K: "M", M: "K", B: "V", D: "H", H: "D", V: "B", N: "N",
  };
  const CODON_TABLE = {
    TTT: "F", TTC: "F", TTA: "L", TTG: "L", TCT: "S", TCC: "S", TCA: "S", TCG: "S",
    TAT: "Y", TAC: "Y", TAA: "*", TAG: "*", TGT: "C", TGC: "C", TGA: "*", TGG: "W",
    CTT: "L", CTC: "L", CTA: "L", CTG: "L", CCT: "P", CCC: "P", CCA: "P", CCG: "P",
    CAT: "H", CAC: "H", CAA: "Q", CAG: "Q", CGT: "R", CGC: "R", CGA: "R", CGG: "R",
    ATT: "I", ATC: "I", ATA: "I", ATG: "M", ACT: "T", ACC: "T", ACA: "T", ACG: "T",
    AAT: "N", AAC: "N", AAA: "K", AAG: "K", AGT: "S", AGC: "S", AGA: "R", AGG: "R",
    GTT: "V", GTC: "V", GTA: "V", GTG: "V", GCT: "A", GCC: "A", GCA: "A", GCG: "A",
    GAT: "D", GAC: "D", GAA: "E", GAG: "E", GGT: "G", GGC: "G", GGA: "G", GGG: "G",
  };
  const RESTRICTION_ENZYMES = {
    EcoRI: { motif: "GAATTC", cut: 1 },
    BamHI: { motif: "GGATCC", cut: 1 },
    HindIII: { motif: "AAGCTT", cut: 1 },
    NotI: { motif: "GCGGCCGC", cut: 2 },
    XhoI: { motif: "CTCGAG", cut: 1 },
    NheI: { motif: "GCTAGC", cut: 1 },
    KpnI: { motif: "GGTACC", cut: 5 },
    PstI: { motif: "CTGCAG", cut: 5 },
  };

  const normalizeDna = (raw) => {
    const sequence = cleanRawSequence(raw).replaceAll("U", "T");
    if (!sequence) throw new Error("请输入 DNA 序列。");
    const invalid = [...sequence].find((character) => !DNA_ALPHABET.replace("U", "").includes(character));
    if (invalid) throw new Error(`DNA 序列包含不支持的字符 ${invalid}。`);
    return sequence;
  };

  const reverseComplement = (sequence) =>
    [...sequence].reverse().map((base) => DNA_COMPLEMENT[base] ?? "N").join("");

  const translateDna = (sequence) => {
    let peptide = "";
    for (let index = 0; index <= sequence.length - 3; index += 3) {
      peptide += CODON_TABLE[sequence.slice(index, index + 3)] ?? "X";
    }
    return peptide;
  };

  const findOrfs = (raw, minimumAminoAcids = 20) => {
    const sequence = normalizeDna(raw);
    const strands = [
      { sequence, sign: 1 },
      { sequence: reverseComplement(sequence), sign: -1 },
    ];
    const orfs = [];

    strands.forEach(({ sequence: strand, sign }) => {
      for (let frame = 0; frame < 3; frame += 1) {
        const starts = [];
        for (let index = frame; index <= strand.length - 3; index += 3) {
          const codon = strand.slice(index, index + 3);
          if (codon === "ATG") starts.push(index);
          if (!["TAA", "TAG", "TGA"].includes(codon)) continue;

          starts.forEach((start) => {
            const peptide = translateDna(strand.slice(start, index));
            if (peptide.length < minimumAminoAcids) return;
            const coordinates =
              sign === 1
                ? [start + 1, index + 3]
                : [sequence.length - (index + 2), sequence.length - start];
            orfs.push({
              frame: `${sign > 0 ? "+" : "−"}${frame + 1}`,
              start: Math.min(...coordinates),
              end: Math.max(...coordinates),
              strand: sign,
              peptide,
              aminoAcids: peptide.length,
            });
          });
          starts.length = 0;
        }
      }
    });

    orfs.sort((first, second) => second.aminoAcids - first.aminoAcids || first.start - second.start);
    const gc = [...sequence].filter((base) => base === "G" || base === "C").length;
    return { sequence, gc: (gc / sequence.length) * 100, orfs };
  };

  const scanRestrictionSites = (raw, enzymeNames = Object.keys(RESTRICTION_ENZYMES)) => {
    const sequence = normalizeDna(raw);
    const hits = enzymeNames.map((name) => {
      const enzyme = RESTRICTION_ENZYMES[name];
      if (!enzyme) return null;
      const positions = [];
      let index = sequence.indexOf(enzyme.motif);
      while (index !== -1) {
        positions.push(index + 1);
        index = sequence.indexOf(enzyme.motif, index + 1);
      }
      return {
        name,
        motif: enzyme.motif,
        positions,
        cuts: positions.map((position) => position - 1 + enzyme.cut),
      };
    }).filter(Boolean);
    const cuts = [...new Set(hits.flatMap((hit) => hit.cuts))]
      .filter((position) => position > 0 && position < sequence.length)
      .sort((first, second) => first - second);
    const boundaries = [0, ...cuts, sequence.length];
    const fragments = boundaries.slice(1).map((boundary, index) => boundary - boundaries[index]);
    return { sequence, hits, cuts, fragments };
  };

  const api = {
    cleanRawSequence,
    deduplicateFasta,
    findOrfs,
    inferSequenceType,
    needlemanWunsch,
    parseFasta,
    reverseComplement,
    scanLiabilities,
    scanRestrictionSites,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;

  const platform = document.querySelector("[data-tool-platform]");
  if (!platform) return;

  const toolLinks = [...document.querySelectorAll("[data-tool-link]")];
  const toolPanels = [...document.querySelectorAll("[data-tool-panel]")];
  const toolIds = new Set(toolPanels.map((panel) => panel.dataset.toolPanel));

  const activateTool = (toolId, shouldScroll = false) => {
    const resolvedId = toolIds.has(toolId) ? toolId : "sequence";
    toolPanels.forEach((panel) => {
      const isActive = panel.dataset.toolPanel === resolvedId;
      panel.hidden = !isActive;
      panel.classList.toggle("active", isActive);
    });
    toolLinks.forEach((link) => {
      const isActive = link.dataset.toolLink === resolvedId;
      link.classList.toggle("active", isActive);
      if (link.closest(".tool-directory")) {
        if (isActive) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      }
    });

    if (shouldScroll) {
      document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  toolLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const toolId = link.dataset.toolLink;
      history.pushState(null, "", `#${toolId}`);
      activateTool(toolId, !link.closest(".tool-directory"));
    });
  });

  window.addEventListener("hashchange", () => {
    const toolId = location.hash.slice(1);
    if (toolIds.has(toolId)) activateTool(toolId);
  });
  const initialToolId = toolIds.has(location.hash.slice(1)) ? location.hash.slice(1) : "sequence";
  activateTool(initialToolId);
  if (toolIds.has(location.hash.slice(1))) {
    window.requestAnimationFrame(() => {
      document.getElementById(initialToolId)?.scrollIntoView({ block: "start" });
    });
  }

  const setText = (element, value) => {
    if (element) element.textContent = value;
  };

  const downloadText = (content, filename, type = "text/plain;charset=utf-8") => {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const wrapSequence = (sequence, width = 80) =>
    sequence.match(new RegExp(`.{1,${width}}`, "g"))?.join("\n") ?? "";

  const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

  const revealResults = (...surfaces) => {
    surfaces.filter(Boolean).forEach((surface) => {
      surface.classList.remove("results-ready");
      void surface.offsetWidth;
      surface.classList.add("results-ready");
      window.setTimeout(() => surface.classList.remove("results-ready"), 720);
    });
  };

  const runToolAction = async (button, surfaces, pendingLabel, action) => {
    if (!button || button.dataset.running === "true") return;
    const originalContent = button.innerHTML;
    button.dataset.running = "true";
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.classList.add("is-running");
    button.replaceChildren();
    const spinner = document.createElement("span");
    spinner.className = "button-spinner";
    spinner.setAttribute("aria-hidden", "true");
    button.append(spinner, document.createTextNode(pendingLabel));
    surfaces.filter(Boolean).forEach((surface) => surface.classList.add("is-calculating"));

    try {
      await wait(420);
      await action();
      revealResults(...surfaces);
    } finally {
      surfaces.filter(Boolean).forEach((surface) => surface.classList.remove("is-calculating"));
      button.innerHTML = originalContent;
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.classList.remove("is-running");
      delete button.dataset.running;
    }
  };

  const fastaTool = document.querySelector("[data-fasta-tool]");
  if (fastaTool) {
    const fileInput = fastaTool.querySelector("[data-fasta-files]");
    const input = fastaTool.querySelector("[data-fasta-input]");
    const counter = fastaTool.querySelector("[data-fasta-counter]");
    const feedback = fastaTool.querySelector("[data-fasta-feedback]");
    const table = fastaTool.querySelector("[data-fasta-table]");
    const resultSurface = fastaTool.querySelector(".utility-results");
    const runButton = fastaTool.querySelector("[data-fasta-run]");
    const downloadButtons = [...fastaTool.querySelectorAll("[data-fasta-download]")];
    let latestUnique = [];

    const setFastaFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback?.classList.toggle("error", error);
    };

    const updateFastaCounter = () => {
      const lines = input.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      const headers = lines.filter((line) => line.startsWith(">")).length;
      const records = headers || lines.length;
      setText(counter, `${records.toLocaleString()} sequences`);
    };

    const resetFastaResults = () => {
      latestUnique = [];
      ["records", "unique", "duplicates", "residues"].forEach((name) =>
        setText(fastaTool.querySelector(`[data-fasta-metric="${name}"]`), "—"),
      );
      table.replaceChildren();
      const row = table.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.textContent = "整理后将在这里显示前 100 条记录。";
      downloadButtons.forEach((button) => {
        button.disabled = true;
      });
    };

    const showFastaResults = () => {
      try {
        const records = parseFasta(input.value);
        const { annotated, unique } = deduplicateFasta(records);
        latestUnique = unique;
        const invalidCount = annotated.filter((record) => record.type === "Invalid").length;
        const duplicateCount = annotated.filter((record) => record.status.startsWith("重复于")).length;
        const residues = records.reduce((total, record) => total + record.length, 0);

        setText(fastaTool.querySelector('[data-fasta-metric="records"]'), records.length.toLocaleString());
        setText(fastaTool.querySelector('[data-fasta-metric="unique"]'), unique.length.toLocaleString());
        setText(fastaTool.querySelector('[data-fasta-metric="duplicates"]'), duplicateCount.toLocaleString());
        setText(fastaTool.querySelector('[data-fasta-metric="residues"]'), residues.toLocaleString());

        table.replaceChildren();
        annotated.slice(0, 100).forEach((record) => {
          const row = table.insertRow();
          [record.id, record.length.toLocaleString(), record.type, record.status].forEach((value) => {
            row.insertCell().textContent = value;
          });
        });

        downloadButtons.forEach((button) => {
          button.disabled = !unique.length;
        });
        const suffix = invalidCount ? `；${invalidCount} 条含非法字符，未纳入导出` : "";
        setFastaFeedback(`已保留 ${unique.length} 条唯一有效序列${suffix}。`);
      } catch (error) {
        resetFastaResults();
        setFastaFeedback(error.message, true);
      }
    };

    fileInput.addEventListener("change", async () => {
      const files = [...fileInput.files];
      if (!files.length) return;
      input.value = (await Promise.all(files.map((file) => file.text()))).join("\n");
      updateFastaCounter();
      setFastaFeedback(`已读取 ${files.length} 个文件；点击“整理记录”开始分析。`);
    });

    input.addEventListener("input", updateFastaCounter);
    runButton.addEventListener("click", () =>
      runToolAction(runButton, [resultSurface], "整理中…", showFastaResults),
    );
    fastaTool.querySelector("[data-fasta-example]").addEventListener("click", () => {
      input.value = [
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS",
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS",
        "ATGGCCTACGTTAACTGA",
      ].join("\n");
      updateFastaCounter();
      resetFastaResults();
      setFastaFeedback("已载入 3 条无标题示例序列；点击“整理记录”开始分析。");
    });
    fastaTool.querySelector("[data-fasta-clear]").addEventListener("click", () => {
      input.value = "";
      fileInput.value = "";
      updateFastaCounter();
      resetFastaResults();
      setFastaFeedback("直接输入时每行一条序列；也兼容带标题的 FASTA。");
    });

    input.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runButton.click();
    });

    downloadButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (!latestUnique.length) return;
        if (button.dataset.fastaDownload === "fasta") {
          const content = latestUnique
            .map((record) => `>${record.id}\n${wrapSequence(record.sequence)}`)
            .join("\n");
          downloadText(`${content}\n`, "vita_unique_sequences.fasta");
        } else {
          const escapeCsv = (value) => `"${String(value).replaceAll('"', '""')}"`;
          const rows = latestUnique.map((record) =>
            [record.id, record.sequence, record.length, record.type].map(escapeCsv).join(","),
          );
          downloadText(
            `id,sequence,length,type\n${rows.join("\n")}\n`,
            "vita_unique_sequences.csv",
            "text/csv;charset=utf-8",
          );
        }
      });
    });

    resetFastaResults();
  }

  const compareTool = document.querySelector("[data-compare-tool]");
  if (compareTool) {
    const firstInput = compareTool.querySelector("[data-compare-a]");
    const secondInput = compareTool.querySelector("[data-compare-b]");
    const feedback = compareTool.querySelector("[data-compare-feedback]");
    const output = compareTool.querySelector("[data-compare-output]");
    const runButton = compareTool.querySelector("[data-compare-run]");
    const resultSurfaces = [
      compareTool.querySelector(".compare-metrics"),
      compareTool.querySelector(".alignment-output"),
    ];
    let latestAlignment = "";

    const setCompareFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback?.classList.toggle("error", error);
    };

    const formatAlignment = (result, width = 72) => {
      const blocks = [];
      for (let index = 0; index < result.length; index += width) {
        blocks.push(
          `A  ${result.alignedA.slice(index, index + width)}\n` +
            `   ${result.markers.slice(index, index + width)}\n` +
            `B  ${result.alignedB.slice(index, index + width)}`,
        );
      }
      return `score ${result.score} · identity ${result.identity.toFixed(2)}%\n\n${blocks.join("\n\n")}`;
    };

    const resetComparisonResults = () => {
      latestAlignment = "";
      ["identity", "matches", "length", "gaps"].forEach((name) =>
        setText(compareTool.querySelector(`[data-compare-metric="${name}"]`), "—"),
      );
      setText(output, "运行后将在这里显示对齐结果。");
    };

    const runComparison = () => {
      try {
        const result = needlemanWunsch(firstInput.value, secondInput.value);
        const values = {
          identity: `${result.identity.toFixed(2)}%`,
          matches: result.matches.toLocaleString(),
          length: result.length.toLocaleString(),
          gaps: result.gaps.toLocaleString(),
        };
        Object.entries(values).forEach(([name, value]) =>
          setText(compareTool.querySelector(`[data-compare-metric="${name}"]`), value),
        );
        latestAlignment = formatAlignment(result);
        setText(output, latestAlignment);
        const alphabetWarning =
          result.typeA === result.typeB
            ? ""
            : ` 字母表推断为 ${result.typeA} / ${result.typeB}，请确认两条输入属于同一分子类型。`;
        setCompareFeedback(
          `全局比对完成；一致性按包含缺口的比对长度计算。${alphabetWarning}`,
        );
      } catch (error) {
        resetComparisonResults();
        setCompareFeedback(error.message, true);
      }
    };

    runButton.addEventListener("click", () =>
      runToolAction(runButton, resultSurfaces, "比对中…", runComparison),
    );
    compareTool.querySelector("[data-compare-example]").addEventListener("click", () => {
      firstInput.value =
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS";
      secondInput.value =
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGATYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYYDYWGQGTLVTVSS";
      resetComparisonResults();
      setCompareFeedback("已载入两条示例序列；点击“开始比对”运行全局比对。");
    });
    [firstInput, secondInput].forEach((input) => {
      input.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runButton.click();
      });
    });
    compareTool.querySelector("[data-compare-copy]").addEventListener("click", async () => {
      if (!latestAlignment) {
        setCompareFeedback("请先完成一次比对。", true);
        return;
      }
      try {
        await navigator.clipboard.writeText(latestAlignment);
        setCompareFeedback("对齐结果已复制。");
      } catch {
        setCompareFeedback("复制未完成，请手动选择结果文本。", true);
      }
    });
  }

  const liabilityTool = document.querySelector("[data-liability-tool]");
  if (liabilityTool) {
    const input = liabilityTool.querySelector("[data-liability-input]");
    const feedback = liabilityTool.querySelector("[data-liability-feedback]");
    const count = liabilityTool.querySelector("[data-liability-count]");
    const table = liabilityTool.querySelector("[data-liability-table]");
    const resultSurface = liabilityTool.querySelector(".liability-summary");
    const runButton = liabilityTool.querySelector("[data-liability-run]");

    const setLiabilityFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback?.classList.toggle("error", error);
    };

    const resetLiabilityResults = () => {
      setText(count, "—");
      table.replaceChildren();
      const row = table.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.textContent = "扫描后将在这里显示结果。";
    };

    const runLiabilityScan = () => {
      try {
        const result = scanLiabilities(input.value);
        setText(count, result.flags.length.toLocaleString());
        table.replaceChildren();
        if (!result.flags.length) {
          const row = table.insertRow();
          const cell = row.insertCell();
          cell.colSpan = 4;
          cell.textContent = "当前规则范围内未发现需优先复核的位点。";
        } else {
          result.flags.forEach((flag) => {
            const row = table.insertRow();
            [flag.category, flag.position, flag.motif, flag.interpretation].forEach((value) => {
              row.insertCell().textContent = value;
            });
          });
        }
        setLiabilityFeedback(
          `已扫描 ${result.sequence.length.toLocaleString()} aa；结果可与结构、制剂和实验数据联合解读。`,
        );
      } catch (error) {
        resetLiabilityResults();
        setLiabilityFeedback(error.message, true);
      }
    };

    runButton.addEventListener("click", () =>
      runToolAction(runButton, [resultSurface], "扫描中…", runLiabilityScan),
    );
    liabilityTool.querySelector("[data-liability-example]").addEventListener("click", () => {
      input.value =
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVANVTNGDGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSSK";
      resetLiabilityResults();
      setLiabilityFeedback("已载入抗体示例序列；点击“扫描位点”开始规则扫描。");
    });
    input.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runButton.click();
    });
  }

  const uniprotTool = document.querySelector("[data-uniprot-tool]");
  if (uniprotTool) {
    const form = uniprotTool.querySelector("[data-uniprot-form]");
    const input = uniprotTool.querySelector("[data-uniprot-input]");
    const feedback = uniprotTool.querySelector("[data-uniprot-feedback]");
    const resultElement = uniprotTool.querySelector("[data-uniprot-result]");
    let controller;

    const setUniprotFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback?.classList.toggle("error", error);
    };

    const valueAt = (value, fallback = "—") => value || fallback;

    const renderUniprotEntry = (entry, release) => {
      const accession = entry.primaryAccession;
      const proteinName =
        entry.proteinDescription?.recommendedName?.fullName?.value ??
        entry.proteinDescription?.submissionNames?.[0]?.fullName?.value ??
        entry.uniProtkbId;
      const gene = entry.genes?.[0]?.geneName?.value;
      const organism = entry.organism?.scientificName;
      const functionText = entry.comments?.find((comment) => comment.commentType === "FUNCTION")
        ?.texts?.[0]?.value;

      resultElement.replaceChildren();
      const entryNode = document.createElement("div");
      entryNode.className = "uniprot-entry";

      const eyebrow = document.createElement("span");
      eyebrow.textContent = `${accession} · ${valueAt(entry.entryType, "UNIPROTKB")}`;
      const title = document.createElement("h4");
      title.textContent = proteinName;
      const subtitle = document.createElement("p");
      subtitle.textContent = `${valueAt(gene, "Gene 未标注")} · ${valueAt(organism, "物种未标注")}`;
      entryNode.append(eyebrow, title, subtitle);

      const facts = document.createElement("div");
      facts.className = "uniprot-facts";
      [
        ["Entry name", entry.uniProtkbId],
        ["Sequence length", entry.sequence?.length ? `${entry.sequence.length} aa` : null],
        ["UniProt release", release],
      ].forEach(([label, value]) => {
        const fact = document.createElement("div");
        const factLabel = document.createElement("small");
        const factValue = document.createElement("strong");
        factLabel.textContent = label;
        factValue.textContent = valueAt(value);
        fact.append(factLabel, factValue);
        facts.append(fact);
      });
      entryNode.append(facts);

      const functionBlock = document.createElement("div");
      functionBlock.className = "uniprot-function";
      const functionLabel = document.createElement("strong");
      functionLabel.textContent = "FUNCTION";
      const functionParagraph = document.createElement("p");
      functionParagraph.textContent = valueAt(functionText, "功能注释可在 UniProt 完整条目中继续查看。");
      functionBlock.append(functionLabel, functionParagraph);
      entryNode.append(functionBlock);

      const officialLink = document.createElement("a");
      officialLink.href = `https://www.uniprot.org/uniprotkb/${encodeURIComponent(accession)}/entry`;
      officialLink.target = "_blank";
      officialLink.rel = "noreferrer";
      officialLink.textContent = "查看 UniProt 完整条目 ↗";
      entryNode.append(officialLink);
      resultElement.append(entryNode);
    };

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const accession = input.value.trim().toUpperCase();
      if (!/^[A-Z0-9]{6,10}$/.test(accession)) {
        setUniprotFeedback("请输入 6–10 位字母数字 accession，例如 P04637。", true);
        return;
      }

      controller?.abort();
      controller = new AbortController();
      resultElement.classList.add("loading");
      setUniprotFeedback(`正在查询 ${accession}…`);

      try {
        const fields = [
          "accession",
          "id",
          "protein_name",
          "gene_names",
          "organism_name",
          "length",
          "cc_function",
        ].join(",");
        const url =
          "https://rest.uniprot.org/uniprotkb/search?" +
          new URLSearchParams({
            query: `accession:${accession}`,
            format: "json",
            fields,
            size: "1",
          });
        const response = await fetch(url, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`UniProt 返回 HTTP ${response.status}`);
        const payload = await response.json();
        const entry = payload.results?.[0];
        if (!entry) throw new Error(`没有找到 accession ${accession}。`);
        renderUniprotEntry(entry, response.headers.get("x-uniprot-release"));
        setUniprotFeedback(`已读取 ${accession} 的蛋白条目，序列与注释信息已更新。`);
      } catch (error) {
        if (error.name === "AbortError") return;
        resultElement.replaceChildren();
        const placeholder = document.createElement("div");
        placeholder.className = "uniprot-placeholder";
        const label = document.createElement("span");
        label.textContent = "QUERY FAILED";
        const title = document.createElement("strong");
        title.textContent = "暂时无法读取蛋白条目";
        const detail = document.createElement("p");
        detail.textContent = error.message;
        placeholder.append(label, title, detail);
        resultElement.append(placeholder);
        setUniprotFeedback(`${error.message} 可稍后重试或打开 UniProt 官网查询。`, true);
      } finally {
        resultElement.classList.remove("loading");
      }
    });
  }

  const orfTool = document.querySelector("[data-orf-tool]");
  if (orfTool) {
    const input = orfTool.querySelector("[data-orf-input]");
    const minimumInput = orfTool.querySelector("[data-orf-min-length]");
    const counter = orfTool.querySelector("[data-orf-counter]");
    const feedback = orfTool.querySelector("[data-orf-feedback]");
    const table = orfTool.querySelector("[data-orf-table]");
    const runButton = orfTool.querySelector("[data-orf-run]");
    const resultSurface = orfTool.querySelector("[data-orf-results]");

    const setOrfFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback.classList.toggle("error", error);
    };

    const updateOrfCounter = () => {
      const length = cleanRawSequence(input.value).length;
      setText(counter, `${length.toLocaleString()} nt`);
    };

    const resetOrfResults = () => {
      ["length", "gc", "count", "longest"].forEach((name) =>
        setText(orfTool.querySelector(`[data-orf-metric="${name}"]`), "—"),
      );
      table.replaceChildren();
      const row = table.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.textContent = "扫描后将在这里显示候选阅读框。";
    };

    const runOrfAnalysis = () => {
      try {
        const minimum = Math.max(1, Math.min(1000, Number(minimumInput.value) || 20));
        minimumInput.value = String(minimum);
        const result = findOrfs(input.value, minimum);
        const longest = result.orfs[0]?.aminoAcids ?? 0;
        const values = {
          length: result.sequence.length.toLocaleString(),
          gc: `${result.gc.toFixed(1)}%`,
          count: result.orfs.length.toLocaleString(),
          longest: `${longest.toLocaleString()} aa`,
        };
        Object.entries(values).forEach(([name, value]) =>
          setText(orfTool.querySelector(`[data-orf-metric="${name}"]`), value),
        );

        table.replaceChildren();
        if (!result.orfs.length) {
          const row = table.insertRow();
          const cell = row.insertCell();
          cell.colSpan = 4;
          cell.textContent = `未发现长度达到 ${minimum} aa 的完整 ORF。`;
        } else {
          result.orfs.slice(0, 100).forEach((orf) => {
            const row = table.insertRow();
            [
              orf.frame,
              `${orf.start.toLocaleString()}–${orf.end.toLocaleString()}`,
              `${orf.aminoAcids.toLocaleString()} aa`,
              `${orf.peptide.slice(0, 34)}${orf.peptide.length > 34 ? "…" : ""}`,
            ].forEach((value) => {
              row.insertCell().textContent = value;
            });
          });
        }
        setOrfFeedback(
          `六阅读框扫描完成，共找到 ${result.orfs.length} 个达到阈值的完整 ORF。`,
        );
      } catch (error) {
        resetOrfResults();
        setOrfFeedback(error.message, true);
      }
    };

    input.addEventListener("input", updateOrfCounter);
    input.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runButton.click();
    });
    runButton.addEventListener("click", () =>
      runToolAction(runButton, [resultSurface], "扫描中…", runOrfAnalysis),
    );
    orfTool.querySelector("[data-orf-example]").addEventListener("click", () => {
      input.value = `GGGATG${"GCT".repeat(32)}TAACCCATG${"GAA".repeat(24)}TAG`;
      updateOrfCounter();
      resetOrfResults();
      setOrfFeedback("已载入包含两个候选阅读框的示例；点击“扫描阅读框”开始分析。");
    });
    resetOrfResults();
    updateOrfCounter();
  }

  const restrictionTool = document.querySelector("[data-restriction-tool]");
  if (restrictionTool) {
    const input = restrictionTool.querySelector("[data-restriction-input]");
    const counter = restrictionTool.querySelector("[data-restriction-counter]");
    const feedback = restrictionTool.querySelector("[data-restriction-feedback]");
    const table = restrictionTool.querySelector("[data-restriction-table]");
    const map = restrictionTool.querySelector("[data-fragment-map]");
    const runButton = restrictionTool.querySelector("[data-restriction-run]");
    const resultSurface = restrictionTool.querySelector("[data-restriction-results]");

    const setRestrictionFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback.classList.toggle("error", error);
    };

    const updateRestrictionCounter = () => {
      setText(counter, `${cleanRawSequence(input.value).length.toLocaleString()} bp`);
    };

    const resetRestrictionResults = () => {
      ["length", "enzymes", "sites", "fragments"].forEach((name) =>
        setText(restrictionTool.querySelector(`[data-restriction-metric="${name}"]`), "—"),
      );
      map.replaceChildren();
      const placeholder = document.createElement("span");
      placeholder.textContent = "运行后生成片段图谱";
      map.append(placeholder);
      table.replaceChildren();
      const row = table.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.textContent = "扫描后将在这里显示酶切位点。";
    };

    const runRestrictionAnalysis = () => {
      try {
        const selected = [
          ...restrictionTool.querySelectorAll('.enzyme-grid input[type="checkbox"]:checked'),
        ].map((checkbox) => checkbox.value);
        if (!selected.length) throw new Error("请至少选择一种限制性内切酶。");
        const result = scanRestrictionSites(input.value, selected);
        const detected = result.hits.filter((hit) => hit.positions.length);
        const siteCount = detected.reduce((total, hit) => total + hit.positions.length, 0);
        const values = {
          length: result.sequence.length.toLocaleString(),
          enzymes: detected.length.toLocaleString(),
          sites: siteCount.toLocaleString(),
          fragments: result.fragments.length.toLocaleString(),
        };
        Object.entries(values).forEach(([name, value]) =>
          setText(restrictionTool.querySelector(`[data-restriction-metric="${name}"]`), value),
        );

        table.replaceChildren();
        result.hits.forEach((hit) => {
          const row = table.insertRow();
          [
            hit.name,
            hit.motif,
            hit.positions.length.toLocaleString(),
            hit.positions.length ? hit.positions.join(", ") : "—",
          ].forEach((value) => {
            row.insertCell().textContent = value;
          });
        });

        map.replaceChildren();
        const total = result.sequence.length;
        result.fragments.forEach((length, index) => {
          const segment = document.createElement("div");
          segment.style.flexGrow = String(Math.max(1, length));
          segment.style.setProperty("--fragment-index", String(index));
          segment.title = `片段 ${index + 1}: ${length.toLocaleString()} bp`;
          const label = document.createElement("span");
          label.textContent = `${length.toLocaleString()} bp`;
          segment.append(label);
          map.append(segment);
        });
        setRestrictionFeedback(
          `酶切图谱已生成：${siteCount} 个切割位点，形成 ${result.fragments.length} 个线性片段。`,
        );
      } catch (error) {
        resetRestrictionResults();
        setRestrictionFeedback(error.message, true);
      }
    };

    input.addEventListener("input", updateRestrictionCounter);
    input.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runButton.click();
    });
    runButton.addEventListener("click", () =>
      runToolAction(runButton, [resultSurface], "绘制中…", runRestrictionAnalysis),
    );
    restrictionTool.querySelector("[data-restriction-example]").addEventListener("click", () => {
      input.value =
        "ATGCGTGAATTCGCTAGCGGATCCAAGCTTGCGGCCGCCTCGAGGGTACCCTGCAGTACGATCGATCG";
      updateRestrictionCounter();
      resetRestrictionResults();
      setRestrictionFeedback("已载入包含多种常用酶切位点的示例；点击“生成酶切图谱”。");
    });
    resetRestrictionResults();
    updateRestrictionCounter();
  }

  const structureTool = document.querySelector("[data-structure-tool]");
  if (structureTool) {
    const form = structureTool.querySelector("[data-structure-form]");
    const input = structureTool.querySelector("[data-structure-input]");
    const label = structureTool.querySelector("[data-structure-label]");
    const feedback = structureTool.querySelector("[data-structure-feedback]");
    const result = structureTool.querySelector("[data-structure-result]");
    const modeButtons = [...structureTool.querySelectorAll("[data-structure-mode]")];
    let mode = "pdb";
    let controller;

    const setStructureFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback.classList.toggle("error", error);
    };

    const setStructureMode = (nextMode) => {
      mode = nextMode;
      modeButtons.forEach((button) => {
        const active = button.dataset.structureMode === mode;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      if (mode === "pdb") {
        setText(label, "PDB ID");
        input.value = "4HHB";
        input.placeholder = "例如 4HHB";
        setStructureFeedback("输入四位 PDB ID，例如 4HHB、1HZH 或 7KMG。");
      } else {
        setText(label, "UniProt accession");
        input.value = "P00533";
        input.placeholder = "例如 P00533";
        setStructureFeedback("输入 UniProt accession，例如 P00533、P04637 或 P0DTC2。");
      }
    };

    const renderStructure = ({ eyebrow, title, subtitle, facts, href, linkText }) => {
      result.replaceChildren();
      const entry = document.createElement("div");
      entry.className = "uniprot-entry structure-entry";
      const eyebrowNode = document.createElement("span");
      eyebrowNode.textContent = eyebrow;
      const titleNode = document.createElement("h4");
      titleNode.textContent = title;
      const subtitleNode = document.createElement("p");
      subtitleNode.textContent = subtitle;
      const factsNode = document.createElement("div");
      factsNode.className = "uniprot-facts";
      facts.forEach(([factLabel, factValue]) => {
        const fact = document.createElement("div");
        const small = document.createElement("small");
        const strong = document.createElement("strong");
        small.textContent = factLabel;
        strong.textContent = factValue ?? "—";
        fact.append(small, strong);
        factsNode.append(fact);
      });
      const link = document.createElement("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = linkText;
      entry.append(eyebrowNode, titleNode, subtitleNode, factsNode, link);
      result.append(entry);
    };

    const queryStructure = async () => {
      try {
        const query = input.value.trim().toUpperCase();
        const valid =
          mode === "pdb" ? /^[A-Z0-9]{4}$/.test(query) : /^[A-Z0-9]{6,10}$/.test(query);
        if (!valid) {
          throw new Error(
            mode === "pdb"
              ? "请输入四位 PDB ID，例如 4HHB。"
              : "请输入 6–10 位 UniProt accession，例如 P00533。",
          );
        }

        controller?.abort();
        controller = new AbortController();
        result.classList.add("loading");
        setStructureFeedback(`正在查询 ${query}…`);

        if (mode === "pdb") {
          const response = await fetch(
            `https://data.rcsb.org/rest/v1/core/entry/${encodeURIComponent(query)}`,
            { signal: controller.signal },
          );
          if (!response.ok) throw new Error(`未找到 PDB 结构 ${query}。`);
          const entry = await response.json();
          const method = entry.exptl?.map((item) => item.method).join(" · ") ?? "实验方法未标注";
          const resolution = entry.rcsb_entry_info?.resolution_combined?.[0];
          renderStructure({
            eyebrow: `${query} · EXPERIMENTAL STRUCTURE`,
            title: entry.struct?.title ?? `PDB ${query}`,
            subtitle: method,
            facts: [
              ["Resolution", resolution ? `${resolution} Å` : "—"],
              ["Polymer entities", String(entry.rcsb_entry_container_identifiers?.polymer_entity_ids?.length ?? "—")],
              ["Atom count", entry.rcsb_entry_info?.deposited_atom_count?.toLocaleString() ?? "—"],
              ["Release date", entry.rcsb_accession_info?.initial_release_date?.slice(0, 10) ?? "—"],
            ],
            href: `https://www.rcsb.org/structure/${encodeURIComponent(query)}`,
            linkText: "打开结构视图 ↗",
          });
        } else {
          const response = await fetch(
            `https://alphafold.ebi.ac.uk/api/prediction/${encodeURIComponent(query)}`,
            { signal: controller.signal },
          );
          if (!response.ok) throw new Error(`未找到 AlphaFold 模型 ${query}。`);
          const models = await response.json();
          const model = models[0];
          if (!model) throw new Error(`未找到 AlphaFold 模型 ${query}。`);
          renderStructure({
            eyebrow: `${query} · PREDICTED STRUCTURE`,
            title: model.uniprotDescription ?? model.uniprotId ?? query,
            subtitle: [model.gene, model.organismScientificName].filter(Boolean).join(" · ") || "预测模型",
            facts: [
              ["Mean pLDDT", model.globalMetricValue ? Number(model.globalMetricValue).toFixed(1) : "—"],
              ["Model version", model.latestVersion ? `v${model.latestVersion}` : "—"],
              ["Model date", model.modelCreatedDate ?? "—"],
              ["Fragment", String(model.uniprotStart && model.uniprotEnd ? `${model.uniprotStart}–${model.uniprotEnd}` : "—")],
            ],
            href: `https://alphafold.ebi.ac.uk/entry/${encodeURIComponent(query)}`,
            linkText: "打开结构模型 ↗",
          });
        }
        setStructureFeedback(`${query} 的结构信息已加载。`);
      } catch (error) {
        if (error.name === "AbortError") return;
        result.replaceChildren();
        const placeholder = document.createElement("div");
        placeholder.className = "uniprot-placeholder";
        const state = document.createElement("span");
        state.textContent = "QUERY FAILED";
        const title = document.createElement("strong");
        title.textContent = "暂时无法读取结构信息";
        const detail = document.createElement("p");
        detail.textContent = error.message;
        placeholder.append(state, title, detail);
        result.append(placeholder);
        setStructureFeedback(error.message, true);
      } finally {
        result.classList.remove("loading");
      }
    };

    modeButtons.forEach((button) =>
      button.addEventListener("click", () => setStructureMode(button.dataset.structureMode)),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const button = form.querySelector(".primary-action");
      runToolAction(button, [result], "查询中…", queryStructure);
    });
  }
})();
