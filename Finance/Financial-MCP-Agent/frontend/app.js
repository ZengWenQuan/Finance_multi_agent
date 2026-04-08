/* ================================================================
   Financial MCP Agent — Frontend Application
   ================================================================ */

// ---------- Agent 元信息配置 ----------
const AGENT_META = {
  fundamental_agent: { icon: "📊", label: "基本面分析", theme: "fundamental" },
  technical_agent:   { icon: "📈", label: "技术分析",   theme: "technical"   },
  value_agent:       { icon: "💰", label: "估值分析",   theme: "value"       },
  news_agent:        { icon: "📰", label: "新闻分析",   theme: "news"        },
  summary_agent:     { icon: "📋", label: "综合报告",   theme: "summary"     },
};

// ---------- 状态 ----------
const state = {
  currentSessionId: null,
  currentStockKey: null,
  currentTaskId: null,
};

// ---------- DOM 引用 ----------
const $ = (id) => document.getElementById(id);
const sessionSelect     = $("sessionSelect");
const refreshSessionsBtn= $("refreshSessionsBtn");
const queryInput        = $("queryInput");
const taskStatusBadge   = $("taskStatusBadge");
const taskMeta          = $("taskMeta");
const agentsContainer   = $("agentsContainer");
const agentCountLabel   = $("agentCountLabel");
const reportContent     = $("reportContent");
const copyReportBtn     = $("copyReportBtn");
const chatMessages      = $("chatMessages");
const chatInput         = $("chatInput");
const sendChatBtn       = $("sendChatBtn");
const progressWrap      = $("progressWrap");
const progressBar       = $("progressBar");
const progressLabel     = $("progressLabel");
const testLlmBtn        = $("testLlmBtn");
const llmStatusDot      = $("llmStatusDot");
const llmStatusText     = $("llmStatusText");

// ---------- 工具函数 ----------
function escapeHtml(text = "") {
  return String(text)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function renderMarkdown(text) {
  if (!text) return '<div class="empty-hint">暂无内容。</div>';
  if (typeof marked !== "undefined") {
    return marked.parse(text);
  }
  // 降级：简单换行处理
  return `<pre style="white-space:pre-wrap;font-size:13px">${escapeHtml(text)}</pre>`;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { const d = await res.json(); detail = d.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

// ---------- 进度条 ----------
let _progressInterval = null;
function startProgress() {
  progressWrap.classList.remove("hidden");
  let pct = 0;
  progressBar.style.width = "0%";
  _progressInterval = setInterval(() => {
    if (pct < 85) { pct += Math.random() * 3; progressBar.style.width = pct + "%"; }
  }, 800);
}
function finishProgress(success = true) {
  clearInterval(_progressInterval);
  progressBar.style.width = "100%";
  progressBar.style.background = success
    ? "linear-gradient(90deg, #34d399, #10b981)"
    : "linear-gradient(90deg, #f87171, #ef4444)";
  setTimeout(() => { progressWrap.classList.add("hidden"); progressBar.style.width = "0%"; progressBar.style.background = ""; }, 1400);
  progressLabel.textContent = success ? "分析完成" : "分析失败";
}

// ---------- 任务状态 ----------
function setTaskStatus(status, meta = {}) {
  taskStatusBadge.textContent = { pending:"等待中", running:"分析中", completed:"已完成", failed:"失败", idle:"Idle" }[status] || status;
  taskStatusBadge.className = `badge ${status}`;
  const lines = [];
  if (state.currentStockKey)  lines.push(`股票: ${state.currentStockKey}`);
  if (state.currentSessionId) lines.push(`会话 ID: ${state.currentSessionId}`);
  if (state.currentTaskId)    lines.push(`任务 ID: ${state.currentTaskId}`);
  if (meta.error)             lines.push(`错误: ${meta.error}`);
  if (meta.report_path)       lines.push(`报告: ${meta.report_path}`);
  taskMeta.innerHTML = lines.map(l => `<div>${escapeHtml(l)}</div>`).join("");
}

function buildStockOptionLabel(session) {
  const companyName = session.company_name || session.session_name || "未知标的";
  const stockCode = session.stock_code || "未识别代码";
  return `${companyName} (${stockCode})`;
}

function buildStockKey(session) {
  if (session.stock_code || session.company_name) {
    return `${session.company_name || "未知标的"} (${session.stock_code || "未识别代码"})`;
  }
  return session.session_name || `session-${session.id}`;
}

// ---------- 加载股票列表 ----------
async function loadSessions() {
  const sessions = await api("/api/sessions");
  sessionSelect.innerHTML = "";
  const latestSessionByStock = new Map();
  sessions.forEach((session) => {
    const stockKey = buildStockKey(session);
    if (!latestSessionByStock.has(stockKey)) {
      latestSessionByStock.set(stockKey, session);
    }
  });
  const stockSessions = Array.from(latestSessionByStock.values());
  const ph = document.createElement("option");
  ph.value = "";
  ph.textContent = stockSessions.length ? "选择股票…" : "暂无股票";
  sessionSelect.appendChild(ph);
  stockSessions.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.id;
    const statusIcon = { completed:"✓", running:"⏳", failed:"✗" }[s.status] || "·";
    opt.textContent = `${statusIcon} ${buildStockOptionLabel(s)}`;
    sessionSelect.appendChild(opt);
  });
  if (stockSessions.length && !state.currentSessionId) {
    sessionSelect.value = String(stockSessions[0].id);
    await loadSessionDetails(stockSessions[0].id);
  }
}

// ---------- 渲染 Agent 结果列表 ----------
function renderAgents(items, agentStatus = {}) {
  agentsContainer.innerHTML = "";
  
  // 预定义显示的顺序
  const order = ["fundamental_agent", "technical_agent", "value_agent", "news_agent"];
  
  // 建立已加载数据的 Map
  const itemMap = new Map();
  if (items) {
    items.forEach(item => itemMap.set(item.agent_name, item));
  }

  // 按照顺序渲染
  order.forEach(agentName => {
    const item = itemMap.get(agentName);
    const status = agentStatus[agentName] || (item ? item.status : "pending");
    
    if (item) {
        // 如果数据库有结果，渲染结果卡片
        agentsContainer.appendChild(buildAgentCard(item, status));
    } else {
        // 如果没有结果，渲染状态卡片
        agentsContainer.appendChild(buildPlaceholderCard(agentName, status));
    }
  });

  if (items && items.length) {
    agentCountLabel.textContent = `${items.length} 个分析 Agent 完成`;
  } else {
    agentCountLabel.textContent = "准备分析中...";
  }
}

function buildPlaceholderCard(agentName, status) {
  const meta = AGENT_META[agentName] || { icon: "🤖", label: agentName, theme: "" };
  const wrapper = document.createElement("div");
  wrapper.className = `accordion-item ${status === 'running' ? 'pulse' : ''}`;

  const statusLabel = { "running": "正在分析...", "pending": "等待中...", "failed": "分析失败" }[status] || "等待中...";
  const badgeCls = status === "running" ? "running" : "pending";

  wrapper.innerHTML = `
    <div class="accordion-toggle no-hover">
      <div class="agent-icon ${meta.theme} ${status === 'running' ? 'spinning' : 'grayscale'}">${meta.icon}</div>
      <div class="agent-info">
        <div class="agent-name">${escapeHtml(meta.label)}</div>
        <div class="agent-meta">
          <span class="badge ${badgeCls}">${statusLabel}</span>
        </div>
      </div>
    </div>`;
  return wrapper;
}

function buildAgentCard(item) {
  const meta = AGENT_META[item.agent_name] || { icon: "🤖", label: item.display_title, theme: "" };
  const sd = item.structured_data_json || {};
  const execTime = sd.execution_time || null;

  const wrapper = document.createElement("div");
  wrapper.className = "accordion-item";

  // ---- 折叠头 ----
  const toggle = document.createElement("button");
  toggle.className = "accordion-toggle";
  toggle.innerHTML = `
    <div class="agent-icon ${meta.theme}">${meta.icon}</div>
    <div class="agent-info">
      <div class="agent-name">${escapeHtml(meta.label)}</div>
      <div class="agent-meta">
        <span class="badge ${item.status}">${escapeHtml(item.status)}</span>
        ${execTime ? `<span>⏱ ${escapeHtml(execTime)}</span>` : ""}
        <span>${escapeHtml(item.updated_at ? item.updated_at.slice(0,16).replace("T"," ") : "")}</span>
      </div>
    </div>
    <svg class="chevron" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
      <path d="M5 8l5 5 5-5"/>
    </svg>`;
  toggle.addEventListener("click", () => wrapper.classList.toggle("open"));
  wrapper.appendChild(toggle);

  // ---- 展开体 ----
  const body = document.createElement("div");
  body.className = "accordion-body";
  body.appendChild(buildAgentBody(item, sd));
  wrapper.appendChild(body);

  return wrapper;
}

function buildAgentBody(item, sd) {
  const frag = document.createDocumentFragment();

  // 根据 agent 类型渲染结构化可视化
  const visualSection = buildVisualSection(item.agent_name, sd, item.content);
  if (visualSection) frag.appendChild(visualSection);

  const structuredSection = buildStructuredOutputSection(sd);
  if (structuredSection) frag.appendChild(structuredSection);

  // 原文分析文本（折叠显示）
  if (item.content) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">分析原文</div>`;
    const textBox = document.createElement("div");
    textBox.className = "markdown-body";
    textBox.style.fontSize = "12px";
    textBox.innerHTML = renderMarkdown(item.content);
    sec.appendChild(textBox);
    frag.appendChild(sec);
  }

  // 执行调试信息
  if (item.execution_trace_json && Object.keys(item.execution_trace_json).length) {
    const sec = buildDebugSection(item.execution_trace_json);
    frag.appendChild(sec);
  }

  return frag;
}

// ---------- 各 Agent 结构化可视化 ----------
function buildVisualSection(agentName, sd, rawContent) {
  switch (agentName) {
    case "fundamental_agent": return buildFundamentalVisual(sd);
    case "technical_agent":   return buildTechnicalVisual(sd);
    case "value_agent":       return buildValueVisual(sd);
    case "news_agent":        return buildNewsVisual(sd);
    case "summary_agent":     return null; // 摘要直接在报告面板显示
    default:                  return null;
  }
}

function hasRenderableStructuredFields(sd = {}) {
  return Object.entries(sd).some(([key, value]) => {
    if (["analysis_text", "raw_analysis", "execution_time", "executed", "error"].includes(key)) {
      return false;
    }
    if (value == null) return false;
    if (typeof value === "string") return value.trim().length > 0;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "object") return Object.keys(value).length > 0;
    return true;
  });
}

function buildStructuredOutputSection(sd = {}) {
  if (!hasRenderableStructuredFields(sd)) return null;

  const sec = document.createElement("div");
  sec.innerHTML = `<div class="section-title">结构化结果</div>`;

  Object.entries(sd).forEach(([key, value]) => {
    if (["analysis_text", "raw_analysis", "execution_time", "executed", "error"].includes(key)) {
      return;
    }
    if (value == null) return;
    if (typeof value === "string" && !value.trim()) return;
    if (Array.isArray(value) && !value.length) return;
    if (typeof value === "object" && !Array.isArray(value) && !Object.keys(value).length) return;

    const block = document.createElement("div");
    block.style.marginBottom = "12px";

    const title = document.createElement("div");
    title.className = "chip-label";
    title.style.marginBottom = "6px";
    title.textContent = key;
    block.appendChild(title);

    block.appendChild(renderStructuredValue(value));
    sec.appendChild(block);
  });

  return sec.childElementCount > 1 ? sec : null;
}

function renderStructuredValue(value) {
  if (Array.isArray(value)) {
    if (value.every(item => typeof item === "string" || typeof item === "number" || typeof item === "boolean")) {
      const list = document.createElement("div");
      list.className = "risk-flags";
      value.forEach(item => {
        const row = document.createElement("div");
        row.className = "risk-flag";
        row.innerHTML = `<span>•</span><span>${escapeHtml(String(item))}</span>`;
        list.appendChild(row);
      });
      return list;
    }

    const pre = document.createElement("pre");
    pre.className = "json-block";
    pre.style.display = "block";
    pre.textContent = JSON.stringify(value, null, 2);
    return pre;
  }

  if (typeof value === "object") {
    return buildMetricCards(value);
  }

  const text = document.createElement("div");
  text.className = "markdown-body";
  text.innerHTML = renderMarkdown(String(value));
  return text;
}

/* ---- 基本面：指标卡片 + 风险提示 ---- */
function buildFundamentalVisual(sd) {
  const wrap = document.createElement("div");

  // 指标卡片
  wrap.innerHTML = `<div class="section-title">核心指标</div>`;

  // profitability_metrics 或 fallback 到文本提取的占位
  const pm = sd.profitability_metrics;
  const gm = sd.growth_metrics;
  const sm = sd.solvency_metrics;

  const allMetrics = { ...(pm || {}), ...(gm || {}), ...(sm || {}) };
  if (Object.keys(allMetrics).length) {
    wrap.appendChild(buildMetricCards(allMetrics));
  } else {
    // 暂无结构化数据时显示提示
    const ph = document.createElement("div");
    ph.className = "empty-hint";
    ph.style.padding = "8px 0";
    ph.textContent = "结构化指标将在下次分析后填充";
    wrap.appendChild(ph);
  }

  // 投资结论
  if (sd.investment_conclusion) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">投资结论</div>
      <div class="chip-row"><div class="chip">
        <span class="chip-val">${escapeHtml(sd.investment_conclusion)}</span>
      </div></div>`;
    wrap.appendChild(sec);
  }

  // 风险标志
  if (sd.risk_flags && sd.risk_flags.length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">风险提示</div>`;
    const list = document.createElement("div");
    list.className = "risk-flags";
    sd.risk_flags.forEach(f => {
      const item = document.createElement("div");
      item.className = "risk-flag";
      item.innerHTML = `<span>⚠</span><span>${escapeHtml(f)}</span>`;
      list.appendChild(item);
    });
    sec.appendChild(list);
    wrap.appendChild(sec);
  }

  return wrap;
}

/* ---- 技术面：价格摘要 + 趋势/信号 chip ---- */
function buildTechnicalVisual(sd) {
  const wrap = document.createElement("div");
  wrap.innerHTML = `<div class="section-title">技术摘要</div>`;

  const chips = [];
  if (sd.trend_analysis) {
    const trendClass = { "上升趋势":"pos", "下降趋势":"neg", "震荡盘整":"neu" }[sd.trend_analysis] || "neu";
    chips.push({ label: "趋势", value: sd.trend_analysis, cls: trendClass });
  }
  if (sd.short_term_signal) {
    const sigClass = { "买入":"buy", "卖出":"sell", "观望":"hold" }[sd.short_term_signal] || "neu";
    chips.push({ label: "短期信号", value: sd.short_term_signal, cls: sigClass });
  }

  if (chips.length) {
    const row = document.createElement("div");
    row.className = "chip-row";
    chips.forEach(c => {
      const chip = document.createElement("div");
      chip.className = "chip";
      chip.innerHTML = `<span class="chip-label">${escapeHtml(c.label)}</span>
        <span class="tag ${c.cls}">${escapeHtml(c.value)}</span>`;
      row.appendChild(chip);
    });
    wrap.appendChild(row);
  }

  // latest_price_summary 指标卡片
  if (sd.latest_price_summary && Object.keys(sd.latest_price_summary).length) {
    wrap.appendChild(buildMetricCards(sd.latest_price_summary));
  }

  // 指标摘要（MACD/KDJ 等）
  if (sd.indicator_summary && Object.keys(sd.indicator_summary).length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">技术指标</div>`;
    sec.appendChild(buildMetricCards(sd.indicator_summary));
    wrap.appendChild(sec);
  }

  // 支撑 / 阻力
  if (sd.support_levels?.length || sd.resistance_levels?.length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">支撑与阻力</div>`;
    const row = document.createElement("div");
    row.className = "chip-row";
    (sd.support_levels || []).forEach(v => {
      const c = document.createElement("div"); c.className = "chip";
      c.innerHTML = `<span class="chip-label">支撑</span><span class="chip-val tag pos">${v}</span>`;
      row.appendChild(c);
    });
    (sd.resistance_levels || []).forEach(v => {
      const c = document.createElement("div"); c.className = "chip";
      c.innerHTML = `<span class="chip-label">阻力</span><span class="chip-val tag neg">${v}</span>`;
      row.appendChild(c);
    });
    sec.appendChild(row);
    wrap.appendChild(sec);
  }

  if (!chips.length && !sd.latest_price_summary) {
    const ph = document.createElement("div");
    ph.className = "empty-hint"; ph.style.padding = "8px 0";
    ph.textContent = "结构化技术指标将在下次分析后填充";
    wrap.appendChild(ph);
  }

  return wrap;
}

/* ---- 估值：估值指标卡片 + 结论标签 ---- */
function buildValueVisual(sd) {
  const wrap = document.createElement("div");
  wrap.innerHTML = `<div class="section-title">估值指标</div>`;

  const vm = sd.valuation_metrics;
  const mvm = sd.market_value_summary;
  const allMetrics = { ...(mvm || {}), ...(vm || {}) };

  if (Object.keys(allMetrics).length) {
    wrap.appendChild(buildMetricCards(allMetrics));
  } else {
    const ph = document.createElement("div");
    ph.className = "empty-hint"; ph.style.padding = "8px 0";
    ph.textContent = "结构化估值指标将在下次分析后填充";
    wrap.appendChild(ph);
  }

  // 估值结论标签
  if (sd.valuation_conclusion) {
    const clsMap = { "低估":"pos", "合理":"neu", "高估":"neg" };
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">估值结论</div>
      <div class="chip-row">
        <div class="chip">
          <span class="chip-label">当前估值</span>
          <span class="tag ${clsMap[sd.valuation_conclusion] || 'neu'}">${escapeHtml(sd.valuation_conclusion)}</span>
        </div>
      </div>`;
    wrap.appendChild(sec);
  }

  // 同行对比表格
  if (sd.peer_comparison && sd.peer_comparison.length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">同行对比</div>`;
    sec.appendChild(buildPeerTable(sd.peer_comparison));
    wrap.appendChild(sec);
  }

  // 股息收益
  if (sd.dividend_yield_summary && Object.keys(sd.dividend_yield_summary).length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">股息收益</div>`;
    sec.appendChild(buildMetricCards(sd.dividend_yield_summary));
    wrap.appendChild(sec);
  }

  return wrap;
}

/* ---- 新闻：情绪标签 + 新闻列表 ---- */
function buildNewsVisual(sd) {
  const wrap = document.createElement("div");
  wrap.innerHTML = `<div class="section-title">舆情概览</div>`;

  // 情绪标签
  if (sd.sentiment_summary) {
    const clsMap = { "正面":"pos", "中性":"neu", "负面":"neg" };
    const row = document.createElement("div");
    row.className = "chip-row";
    row.innerHTML = `
      <div class="chip">
        <span class="chip-label">整体情绪</span>
        <span class="tag ${clsMap[sd.sentiment_summary] || 'neu'}">${escapeHtml(sd.sentiment_summary)}</span>
      </div>`;
    wrap.appendChild(row);
  }

  // 关键事件
  if (sd.key_events && sd.key_events.length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">关键事件</div>`;
    const list = document.createElement("div");
    list.className = "risk-flags";
    list.style.borderLeftColor = "var(--accent)";
    sd.key_events.forEach(e => {
      const item = document.createElement("div");
      item.className = "risk-flag";
      item.style.background = "var(--accent-dim)";
      item.style.borderLeftColor = "var(--accent)";
      item.innerHTML = `<span>📌</span><span>${escapeHtml(e)}</span>`;
      list.appendChild(item);
    });
    sec.appendChild(list);
    wrap.appendChild(sec);
  }

  // 新闻列表
  if (sd.news_items && sd.news_items.length) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">新闻列表</div>`;
    const list = document.createElement("div");
    list.className = "news-list";
    sd.news_items.forEach(n => {
      const nitem = document.createElement("div");
      nitem.className = "news-item";
      const sentScore = n.sentiment_score;
      let sentTag = "";
      if (sentScore != null) {
        const scls = sentScore > 0.2 ? "pos" : sentScore < -0.2 ? "neg" : "neu";
        const slabel = sentScore > 0.2 ? "利好" : sentScore < -0.2 ? "利空" : "中性";
        sentTag = `<span class="tag ${scls}">${slabel}</span>`;
      }
      const titleHtml = n.url
        ? `<a href="${escapeHtml(n.url)}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none">${escapeHtml(n.title || "无标题")}</a>`
        : escapeHtml(n.title || "无标题");
      nitem.innerHTML = `
        <div class="news-title">${titleHtml}</div>
        <div class="news-meta">
          ${n.source ? `<span>${escapeHtml(n.source)}</span>` : ""}
          ${sentTag}
          ${n.summary ? `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(n.summary)}</span>` : ""}
        </div>`;
      list.appendChild(nitem);
    });
    sec.appendChild(list);
    wrap.appendChild(sec);
  }

  // 结论
  if (sd.news_based_conclusion) {
    const sec = document.createElement("div");
    sec.innerHTML = `<div class="section-title">新闻结论</div>
      <div class="chip-row"><div class="chip">
        <span class="chip-val">${escapeHtml(sd.news_based_conclusion)}</span>
      </div></div>`;
    wrap.appendChild(sec);
  }

  if (!sd.sentiment_summary && !sd.news_items?.length) {
    const ph = document.createElement("div");
    ph.className = "empty-hint"; ph.style.padding = "8px 0";
    ph.textContent = "新闻结构化数据将在下次分析后填充";
    wrap.appendChild(ph);
  }

  return wrap;
}

/* ---- 通用：指标卡片网格 ---- */
function buildMetricCards(obj) {
  const grid = document.createElement("div");
  grid.className = "metric-cards";
  Object.entries(obj).forEach(([k, v]) => {
    const card = document.createElement("div");
    card.className = "metric-card";
    const valStr = String(v ?? "—");
    // 判断涨跌方向（简单启发）
    const isUp = valStr.startsWith("+") || valStr.includes("涨");
    const isDown = valStr.startsWith("-") || valStr.includes("跌");
    const valCls = isUp ? " up" : isDown ? " down" : "";
    card.innerHTML = `
      <div class="mc-label" title="${escapeHtml(k)}">${escapeHtml(k)}</div>
      <div class="mc-value${valCls}">${escapeHtml(valStr)}</div>`;
    grid.appendChild(card);
  });
  return grid;
}

/* ---- 同行对比表格 ---- */
function buildPeerTable(peers) {
  if (!peers.length) return document.createTextNode("");
  const keys = Object.keys(peers[0]);
  const table = document.createElement("table");
  table.style.cssText = "width:100%;border-collapse:collapse;font-size:12px";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr>${keys.map(k => `<th style="background:rgba(56,189,248,0.1);color:var(--accent);padding:6px 8px;text-align:left">${escapeHtml(k)}</th>`).join("")}</tr>`;
  const tbody = document.createElement("tbody");
  peers.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = keys.map(k => `<td style="padding:5px 8px;border-bottom:1px solid var(--panel-border)">${escapeHtml(String(row[k] ?? "—"))}</td>`).join("");
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
  return table;
}

/* ---- 调试 Trace Section ---- */
function buildDebugSection(trace) {
  const wrap = document.createElement("div");
  wrap.className = "debug-section";
  const title = document.createElement("div");
  title.className = "section-title";
  title.style.display = "flex";
  title.style.justifyContent = "space-between";
  title.style.cursor = "pointer";

  // 工具调用统计
  const toolCalls = trace.tool_calls || [];
  const agentExec = trace.agent_execution || {};
  const execTime = agentExec.execution_time;
  title.innerHTML = `<span>调试信息</span>
    <span style="color:var(--ink-3);font-weight:400">
      ${toolCalls.length ? `${toolCalls.length} 次工具调用` : ""}
      ${execTime ? ` · ⏱ ${String(execTime).slice(0,8)}` : ""}
    </span>`;

  const jsonBlock = document.createElement("div");
  jsonBlock.className = "json-block hidden";
  title.addEventListener("click", () => jsonBlock.classList.toggle("hidden"));

  // 工具调用摘要
  if (toolCalls.length) {
    const summary = toolCalls.map(t =>
      `[${t.tool_name || t.name || "?"}] ${String(t.status || t.result || "").slice(0, 60)}`
    ).join("\n");
    jsonBlock.textContent = summary + "\n\n--- 完整 Trace ---\n" + JSON.stringify(trace, null, 2);
  } else {
    jsonBlock.textContent = JSON.stringify(trace, null, 2);
  }

  wrap.appendChild(title);
  wrap.appendChild(jsonBlock);
  return wrap;
}

// ---------- 渲染综合报告 ----------
function renderReport(report) {
  if (!report || !report.final_report) {
    reportContent.innerHTML = '<div class="empty-hint">当前会话还没有综合报告。</div>';
    copyReportBtn.classList.add("hidden");
    return;
  }
  reportContent.innerHTML = `<div class="markdown-body">${renderMarkdown(report.final_report)}</div>`;
  copyReportBtn.classList.remove("hidden");
  copyReportBtn._reportText = report.final_report;
}

// ---------- 渲染聊天记录 ----------
function renderMessages(messages) {
  chatMessages.innerHTML = "";
  if (!messages || !messages.length) {
    chatMessages.innerHTML = '<div class="empty-hint">还没有聊天记录。可以基于上方报告提问。</div>';
    return;
  }
  messages.forEach(msg => {
    const div = document.createElement("div");
    div.className = `chat-message ${msg.role}`;
    const roleLabel = { user:"用户", assistant:"研究助理", system:"系统" }[msg.role] || msg.role;
    div.innerHTML = `<div class="msg-role">${escapeHtml(roleLabel)}</div>
      <div class="msg-body">${renderMarkdown(msg.content)}</div>`;
    chatMessages.appendChild(div);
  });
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ---------- 加载会话详情 ----------
async function loadSessionDetails(sessionId, taskData = null) {
  state.currentSessionId = Number(sessionId);
  const [session, agents, report, messages] = await Promise.all([
    api(`/api/sessions/${sessionId}`).catch(() => null),
    api(`/api/sessions/${sessionId}/agents`).catch(() => []),
    api(`/api/sessions/${sessionId}/report`).catch(() => null),
    api(`/api/sessions/${sessionId}/messages`).catch(() => []),
  ]);
  state.currentStockKey = session ? buildStockKey(session) : null;

  // 如果任务正在运行，优先显示任务状态
  const agentStatus = taskData ? (taskData.agent_status || {}) : {};
  renderAgents(agents, agentStatus);
  renderReport(report);

  // 针对摘要 Agent 的特殊处理：如果任务正在运行且处于摘要阶段，显示摘要正在生成
  if (agentStatus.summary_agent === "running") {
      reportContent.innerHTML = '<div class="loading-report">综合报告正在生成中，请稍候...</div>';
  } else {
      renderReport(report);
  }

  renderMessages(messages);
  if (!taskData) setTaskStatus("idle");
}

// ---------- 事件绑定 ----------

// ========== 分步工作流 ==========
const parseBtn = $("parseBtn");
const parseResult = $("parseResult");
const summarizeBtn = $("summarizeBtn");
const summaryHint = $("summaryHint");
const analystBtns = document.querySelectorAll(".analyst-btn");

// 步骤 1：解析
parseBtn.addEventListener("click", async () => {
  const userQuery = queryInput.value.trim();
  if (!userQuery) return;
  parseBtn.disabled = true;
  parseBtn.textContent = "解析中…";
  parseBtn.classList.remove("locked", "completed", "failed");
  parseBtn.classList.add("running");
  parseResult.textContent = "";
  parseResult.className = "step-result";
  // 步骤编号进入 running 状态
  const stepNum = document.querySelector("#stepParse .step-num");
  stepNum.classList.remove("done", "fail");
  stepNum.classList.add("running");
  try {
    const result = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ user_query: userQuery, source: "web" }),
    });
    state.currentSessionId = result.session_id;
    state.currentTaskId = result.task_id;
    // 然后调用 parse
    const parseRes = await api(`/api/sessions/${result.session_id}/parse`, {
      method: "POST",
      body: JSON.stringify({ user_query: userQuery }),
    });
    if (parseRes.status === "completed") {
      parseBtn.textContent = "已解析 ✓";
      parseBtn.classList.remove("running");
      parseBtn.classList.add("completed");
      stepNum.classList.remove("running");
      stepNum.classList.add("done");
      parseResult.textContent = `${parseRes.company_name || ""} ${parseRes.stock_code || ""}`.trim();
      // 解锁分析师按钮
      analystBtns.forEach(btn => {
        btn.disabled = false;
        btn.classList.remove("locked", "running", "completed", "failed");
        btn.classList.add("ready");
      });
      state.currentStockKey = `${parseRes.company_name || "未知"} (${parseRes.stock_code || "?"})`;
      startProgress();
      progressLabel.textContent = "解析完成，请选择分析师运行";
    } else {
      parseBtn.textContent = "解析失败 ✗";
      parseBtn.classList.remove("running");
      parseBtn.classList.add("failed");
      parseBtn.disabled = false;
      stepNum.classList.remove("running");
      stepNum.classList.add("fail");
      parseResult.textContent = parseRes.error || "解析失败";
      parseResult.classList.add("error");
    }
  } catch (e) {
    parseBtn.textContent = "解析失败";
    parseBtn.classList.remove("running");
    parseBtn.classList.add("failed");
    parseBtn.disabled = false;
    parseResult.textContent = e.message;
    parseResult.className = "step-result error";
    const stepNum2 = document.querySelector("#stepParse .step-num");
    stepNum2.classList.remove("running");
    stepNum2.classList.add("fail");
  }
});

// 步骤 2：运行单个分析师
analystBtns.forEach(btn => {
  btn.addEventListener("click", async () => {
    const agentName = btn.dataset.agent;
    if (!state.currentSessionId || btn.disabled) return;

    btn.disabled = true;
    btn.classList.remove("ready", "completed", "failed");
    btn.classList.add("running");
    btn.textContent = `${AGENT_META[agentName].icon} ${AGENT_META[agentName].label}…`;
    progressLabel.textContent = `${AGENT_META[agentName].label} 分析中…`;

    // 步骤 2 编号进入 running 状态（至少一个分析师开始运行）
    const step2Num = document.querySelectorAll(".step-num")[1];
    if (step2Num && !step2Num.classList.contains("done")) {
      step2Num.classList.remove("fail");
      step2Num.classList.add("running");
    }

    try {
      await api(`/api/sessions/${state.currentSessionId}/agents/${agentName}`, {
        method: "POST",
      });
      // 开始轮询这个 agent 的状态
      pollAgentStatus(agentName, btn);
    } catch (e) {
      btn.classList.remove("running");
      btn.classList.add("ready");
      btn.disabled = false;
      btn.textContent = `${AGENT_META[agentName].icon} ${AGENT_META[agentName].label}`;
      progressLabel.textContent = e.message;
    }
  });
});

// 轮询单个 agent 状态
async function pollAgentStatus(agentName, btn) {
  if (!state.currentTaskId) return;
  const maxPolls = 300; // 300 * 2s = 10min
  for (let i = 0; i < maxPolls; i++) {
    await new Promise(r => setTimeout(r, 2000));
    try {
      const task = await api(`/api/tasks/${state.currentTaskId}`);
      const status = task.agent_status?.[agentName];
      if (status === "completed") {
        btn.classList.remove("running");
        btn.classList.add("completed");
        btn.textContent = `${AGENT_META[agentName].icon} ${AGENT_META[agentName].label} ✓`;
        // 刷新 agent 结果
        await loadSessionDetails(state.currentSessionId, task);
        checkAllAnalystsDone(task);
        return;
      }
      if (status === "failed") {
        btn.classList.remove("running");
        btn.classList.add("failed");
        btn.disabled = true; // 失败后不允许重试（后端允许 failed 状态重跑，但前端简化处理）
        const err = task.agent_status?.[agentName + "_error"] || "执行失败";
        btn.textContent = `${AGENT_META[agentName].icon} ${AGENT_META[agentName].label} ✗`;
        btn.title = `失败: ${err}（服务端可能允许重跑）`;
        progressLabel.textContent = `${AGENT_META[agentName].label} 失败: ${err}`;
        // 仍然刷新看看有没有部分结果
        await loadSessionDetails(state.currentSessionId, task);
        return;
      }
    } catch {
      return;
    }
  }
  btn.classList.remove("running");
  btn.classList.add("ready");
  btn.disabled = false;
  btn.textContent = `${AGENT_META[agentName].icon} ${AGENT_META[agentName].label}`;
}

// 检查是否所有分析师都完成了
function checkAllAnalystsDone(task) {
  const allDone = ["fundamental_agent", "technical_agent", "value_agent", "news_agent"]
    .every(a => task.agent_status?.[a] === "completed");
  if (allDone) {
    summarizeBtn.disabled = false;
    summarizeBtn.classList.remove("locked", "running", "completed", "failed");
    summarizeBtn.classList.add("ready");
    summaryHint.textContent = "全部完成，可以生成报告";
    summaryHint.style.color = "var(--green)";
    progressLabel.textContent = "全部分析师完成，请生成综合报告";
    finishProgress(true);
    // 步骤 2 编号标记完成
    const step2Num = document.querySelectorAll(".step-num")[1];
    if (step2Num) {
      step2Num.classList.remove("running", "fail");
      step2Num.classList.add("done");
    }
  }
}

// 步骤 3：生成综合报告
summarizeBtn.addEventListener("click", async () => {
  if (!state.currentSessionId) return;
  summarizeBtn.disabled = true;
  summarizeBtn.classList.remove("ready", "completed", "failed");
  summarizeBtn.classList.add("running");
  summarizeBtn.textContent = "生成中…";
  summaryHint.textContent = "";
  const step3Num = document.querySelector("#stepSummary .step-num");
  if (step3Num) {
    step3Num.classList.remove("done", "fail");
    step3Num.classList.add("running");
  }
  startProgress();
  progressLabel.textContent = "综合报告生成中…";
  try {
    await api(`/api/sessions/${state.currentSessionId}/summarize`, { method: "POST" });
    // 轮询 summary 状态
    pollSummaryStatus();
  } catch (e) {
    summarizeBtn.textContent = "失败 ✗";
    summarizeBtn.classList.remove("running");
    summarizeBtn.classList.add("failed");
    summarizeBtn.disabled = false;
    summaryHint.textContent = e.message;
    summaryHint.style.color = "var(--red)";
    if (step3Num) {
      step3Num.classList.remove("running");
      step3Num.classList.add("fail");
    }
  }
});

async function pollSummaryStatus() {
  if (!state.currentTaskId) return;
  const maxPolls = 300;
  for (let i = 0; i < maxPolls; i++) {
    await new Promise(r => setTimeout(r, 2000));
    try {
      const task = await api(`/api/tasks/${state.currentTaskId}`);
      const s = task.agent_status?.["summary_agent"];
      if (s === "completed") {
        summarizeBtn.textContent = "报告已生成 ✓";
        summarizeBtn.classList.remove("running");
        summarizeBtn.classList.add("completed");
        const step3Num = document.querySelector("#stepSummary .step-num");
        if (step3Num) {
          step3Num.classList.remove("running");
          step3Num.classList.add("done");
        }
        summaryHint.textContent = "";
        finishProgress(true);
        setTaskStatus("completed", task);
        await loadSessions();
        await loadSessionDetails(state.currentSessionId, task);
        return;
      }
      if (s === "failed") {
        summarizeBtn.textContent = "失败 ✗";
        summarizeBtn.classList.remove("running");
        summarizeBtn.classList.add("failed");
        summarizeBtn.disabled = false;
        const step3Num = document.querySelector("#stepSummary .step-num");
        if (step3Num) {
          step3Num.classList.remove("running");
          step3Num.classList.add("fail");
        }
        finishProgress(false);
        setTaskStatus("failed", { error: "综合报告生成失败" });
        return;
      }
    } catch {
      return;
    }
  }
  summarizeBtn.classList.remove("running");
  summarizeBtn.classList.add("ready");
  summarizeBtn.disabled = false;
  summarizeBtn.textContent = "超时";
}

// 保留旧的回车键行为
queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    parseBtn.click();
  }
});

refreshSessionsBtn.addEventListener("click", () => loadSessions());

sessionSelect.addEventListener("change", async (e) => {
  const sessionId = e.target.value;
  if (!sessionId) return;
  await loadSessionDetails(sessionId);
});

sendChatBtn.addEventListener("click", async () => {
  if (!state.currentSessionId) { alert("请先选择一只股票或创建新分析"); return; }
  const content = chatInput.value.trim();
  if (!content) return;
  sendChatBtn.disabled = true;
  // 先本地追加用户消息
  const userDiv = document.createElement("div");
  userDiv.className = "chat-message user";
  userDiv.innerHTML = `<div class="msg-role">用户</div><div class="msg-body">${escapeHtml(content)}</div>`;
  chatMessages.appendChild(userDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  chatInput.value = "";

  // 占位"思考中"
  const thinkDiv = document.createElement("div");
  thinkDiv.className = "chat-message assistant";
  thinkDiv.innerHTML = `<div class="msg-role">研究助理</div><div class="msg-body" style="color:var(--ink-3)">思考中…</div>`;
  chatMessages.appendChild(thinkDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  const ragMode = document.getElementById("ragModeSelect").value;
  try {
    const resp = await api(`/api/sessions/${state.currentSessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ role: "user", content, rag_mode: ragMode }),
    });
    // 刷新完整聊天记录
    const messages = await api(`/api/sessions/${state.currentSessionId}/messages`).catch(() => []);
    renderMessages(messages);
  } catch (e) {
    thinkDiv.querySelector(".msg-body").textContent = `错误: ${e.message}`;
  } finally {
    sendChatBtn.disabled = false;
  }
});

// 支持回车发送聊天 (Enter 发送, Shift+Enter 换行)
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChatBtn.click();
  }
});

copyReportBtn.addEventListener("click", () => {
  const text = copyReportBtn._reportText || "";
  navigator.clipboard.writeText(text).then(() => {
    const old = copyReportBtn.textContent;
    copyReportBtn.textContent = "已复制 ✓";
    setTimeout(() => { copyReportBtn.textContent = old; }, 1800);
  });
});

// ---------- 测试 LLM 连通性 ----------
async function testLlm() {
  llmStatusDot.className = "llm-status-dot checking";
  llmStatusText.textContent = "检测中…";
  testLlmBtn.disabled = true;
  testLlmBtn.textContent = "检测中…";
  try {
    const res = await api("/api/health");
    if (res && res.status === "ok") {
      llmStatusDot.className = "llm-status-dot ok";
      llmStatusText.textContent = "LLM 可用";
    } else {
      throw new Error("unexpected response");
    }
  } catch {
    llmStatusDot.className = "llm-status-dot fail";
    llmStatusText.textContent = "LLM 不可用";
  } finally {
    testLlmBtn.disabled = false;
    testLlmBtn.textContent = "测试 LLM";
  }
}

testLlmBtn.addEventListener("click", testLlm);

// ---------- 初始化 ----------
loadSessions().then(() => setTaskStatus("idle"));
