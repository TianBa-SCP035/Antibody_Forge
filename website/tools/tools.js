(() => {
  const DNA_ALPHABET = "ACGTRYSWKMBDHVN";
  const PROTEIN_ALPHABET = "ACDEFGHIKLMNPQRSTVWY";

  const cleanRawSequence = (raw) =>
    String(raw ?? "")
      .split(/\r?\n/)
      .filter((line) => !line.trim().startsWith(">"))
      .join("")
      .replace(/\s/g, "")
      .toUpperCase();

  const inferSequenceType = (sequence) => {
    if (!sequence) return "empty";
    if ([...sequence].every((character) => DNA_ALPHABET.includes(character))) return "DNA";
    if ([...sequence].every((character) => PROTEIN_ALPHABET.includes(character))) return "Protein";
    return "Invalid";
  };

  const parseFasta = (raw) => {
    const lines = String(raw ?? "").replace(/\r\n?/g, "\n").split("\n");
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
      const sequence = record.sequenceParts.join("").replace(/\s/g, "").toUpperCase();
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
      throw new Error("浏览器全局比对请将每条序列控制在 2,000 个字符以内。");
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
        "该 Asn 邻域常被列为脱酰胺复核位点，不能仅凭基序判断反应速率。",
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
          interpretation: `${residue} 残基可能发生氧化；真实风险取决于溶剂暴露、制剂和应力条件。`,
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
        interpretation: "Cys 总数为奇数；不代表必然存在游离巯基，但建议核对链边界与二硫键配对。",
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

  const api = { cleanRawSequence, deduplicateFasta, inferSequenceType, needlemanWunsch, parseFasta, scanLiabilities };
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

  const fastaTool = document.querySelector("[data-fasta-tool]");
  if (fastaTool) {
    const fileInput = fastaTool.querySelector("[data-fasta-files]");
    const input = fastaTool.querySelector("[data-fasta-input]");
    const counter = fastaTool.querySelector("[data-fasta-counter]");
    const feedback = fastaTool.querySelector("[data-fasta-feedback]");
    const table = fastaTool.querySelector("[data-fasta-table]");
    const downloadButtons = [...fastaTool.querySelectorAll("[data-fasta-download]")];
    let latestUnique = [];

    const setFastaFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback?.classList.toggle("error", error);
    };

    const updateFastaCounter = () => {
      const records = (input.value.match(/^>/gm) ?? []).length;
      setText(counter, `${records.toLocaleString()} records`);
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
      setFastaFeedback(`已在本地读取 ${files.length} 个文件；点击“整理记录”开始分析。`);
    });

    input.addEventListener("input", updateFastaCounter);
    fastaTool.querySelector("[data-fasta-run]").addEventListener("click", showFastaResults);
    fastaTool.querySelector("[data-fasta-example]").addEventListener("click", () => {
      input.value = [
        ">VH_candidate_01",
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS",
        ">VH_candidate_01_duplicate",
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS",
        ">DNA_candidate_02",
        "ATGGCCTACGTTAACTGA",
      ].join("\n");
      updateFastaCounter();
      showFastaResults();
    });
    fastaTool.querySelector("[data-fasta-clear]").addEventListener("click", () => {
      input.value = "";
      fileInput.value = "";
      updateFastaCounter();
      resetFastaResults();
      setFastaFeedback("接受标准 FASTA；重复序列保留首次出现的记录名。");
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
          `全局比对已在本地完成；一致性按包含缺口的比对长度计算。${alphabetWarning}`,
        );
      } catch (error) {
        latestAlignment = "";
        ["identity", "matches", "length", "gaps"].forEach((name) =>
          setText(compareTool.querySelector(`[data-compare-metric="${name}"]`), "—"),
        );
        setText(output, "运行后将在这里显示对齐结果。");
        setCompareFeedback(error.message, true);
      }
    };

    compareTool.querySelector("[data-compare-run]").addEventListener("click", runComparison);
    compareTool.querySelector("[data-compare-example]").addEventListener("click", () => {
      firstInput.value =
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSS";
      secondInput.value =
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGATYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYYDYWGQGTLVTVSS";
      runComparison();
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
        setCompareFeedback("浏览器未允许复制，请手动选择结果文本。", true);
      }
    });
  }

  const liabilityTool = document.querySelector("[data-liability-tool]");
  if (liabilityTool) {
    const input = liabilityTool.querySelector("[data-liability-input]");
    const feedback = liabilityTool.querySelector("[data-liability-feedback]");
    const count = liabilityTool.querySelector("[data-liability-count]");
    const table = liabilityTool.querySelector("[data-liability-table]");

    const setLiabilityFeedback = (message, error = false) => {
      setText(feedback, message);
      feedback?.classList.toggle("error", error);
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
          cell.textContent = "当前规则未标记位点；这不代表序列不存在其他开发风险。";
        } else {
          result.flags.forEach((flag) => {
            const row = table.insertRow();
            [flag.category, flag.position, flag.motif, flag.interpretation].forEach((value) => {
              row.insertCell().textContent = value;
            });
          });
        }
        setLiabilityFeedback(
          `已扫描 ${result.sequence.length.toLocaleString()} aa；标记结果用于确定复核优先级，不是修饰预测。`,
        );
      } catch (error) {
        setText(count, "—");
        table.replaceChildren();
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = "扫描后将在这里显示结果。";
        setLiabilityFeedback(error.message, true);
      }
    };

    liabilityTool.querySelector("[data-liability-run]").addEventListener("click", runLiabilityScan);
    liabilityTool.querySelector("[data-liability-example]").addEventListener("click", () => {
      input.value =
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVANVTNGDGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGRGYFDYWGQGTLVTVSSK";
      runLiabilityScan();
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
        ["API release", release],
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
      functionParagraph.textContent = valueAt(functionText, "该精简响应中没有可用的功能注释。");
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
      setUniprotFeedback(`正在通过 UniProt REST API 查询 ${accession}…`);

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
        setUniprotFeedback(`已读取 ${accession} 的公开条目；序列输入未发送。`);
      } catch (error) {
        if (error.name === "AbortError") return;
        resultElement.replaceChildren();
        const placeholder = document.createElement("div");
        placeholder.className = "uniprot-placeholder";
        const label = document.createElement("span");
        label.textContent = "QUERY FAILED";
        const title = document.createElement("strong");
        title.textContent = "暂时无法读取公开条目";
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
})();
