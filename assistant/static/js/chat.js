function chatApp() {
  return {
    status: "connecting",
    draft: "",
    error: "",
    messages: [],
    socket: null,
    retryDelay: 500,
    closedByPage: false,
    pagehideBound: false,
    renderFrame: 0,
    pinned: true,
    lastQuestion: "",

    get statusLabel() {
      if (this.status === "online") return "на зв'язку";
      if (this.status === "offline") return "немає з'єднання";
      return "підключення";
    },

    get started() {
      return this.messages.length > 0;
    },

    get isStreaming() {
      return Boolean(this.currentAssistant());
    },

    get composerState() {
      if (this.isStreaming) return "streaming";
      if (this.draft.trim() && this.status === "online") return "ready";
      return "idle";
    },

    get reconnectLabel() {
      if (this.status === "offline") return "Немає з'єднання. Перепідключення…";
      return "Підключення…";
    },

    boot() {
      this.connect();
      this.bindViewport();
      this.$nextTick(() => {
        this.growInput();
        this.measureLift();
        window.requestAnimationFrame(() => this.measureLift());
      });
    },

    bindViewport() {
      const apply = () => {
        const height = window.visualViewport ? window.visualViewport.height : window.innerHeight;
        this.$root.style.setProperty("--app-h", `${Math.round(height)}px`);
        this.measureLift();
      };
      apply();
      window.addEventListener("resize", apply);
      if (window.ResizeObserver && this.$refs.dock) {
        new ResizeObserver(() => this.measureLift()).observe(this.$refs.dock);
      }
      if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", apply);
        window.visualViewport.addEventListener("scroll", apply);
      }
    },

    measureLift() {
      const dock = this.$refs.dock;
      const feed = this.$refs.feed;
      if (!dock) return;
      this.$root.style.setProperty("--dock-h", `${dock.offsetHeight + 10}px`);
      const slot = this.$refs.slot;
      if (this.started || !slot || !feed) {
        this.$root.style.setProperty("--lift", "0px");
        this.$root.dataset.heroFit = "dock";
        return;
      }
      slot.style.height = `${dock.offsetHeight}px`;
      if (feed.scrollHeight > feed.clientHeight + 8) {
        slot.style.height = "8px";
        this.$root.style.setProperty("--lift", "0px");
        this.$root.dataset.heroFit = "dock";
        return;
      }
      this.$root.dataset.heroFit = "center";
      // offsetTop ignores the dock's transform, so a measurement taken mid-transition stays exact.
      const slotTop = slot.getBoundingClientRect().top - this.$root.getBoundingClientRect().top;
      const lift = Math.max(0, dock.offsetTop - slotTop);
      this.$root.style.setProperty("--lift", `${Math.round(lift)}px`);
    },

    connect() {
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      const path = this.$root.dataset.socket || "/ws/chat/";
      const socket = new WebSocket(`${protocol}://${location.host}${path}`);
      this.socket = socket;
      socket.onopen = () => {
        this.status = "online";
        this.retryDelay = 500;
      };
      socket.onclose = () => {
        this.status = "offline";
        if (this.closedByPage) return;
        window.setTimeout(() => this.connect(), this.retryDelay);
        this.retryDelay = Math.min(this.retryDelay * 2, 8000);
      };
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        this.onEvent(payload);
      };
      if (!this.pagehideBound) {
        this.pagehideBound = true;
        window.addEventListener("pagehide", () => {
          this.closedByPage = true;
          if (this.socket) this.socket.close();
        });
      }
    },

    ask(prompt) {
      this.draft = prompt;
      this.$nextTick(() => {
        this.growInput();
        this.submit();
      });
    },

    onEnter(event) {
      if (event.shiftKey || event.isComposing || event.keyCode === 229) return;
      event.preventDefault();
      this.submit();
    },

    growInput() {
      const input = this.$refs.input;
      if (!input) return;
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
    },

    onInputFocus() {
      if (this.started) this.followLatest(true);
    },

    composerAction() {
      if (this.isStreaming) {
        this.stop();
        return;
      }
      this.submit();
    },

    submit() {
      const question = this.draft.trim();
      if (!question || this.status !== "online" || !this.socket || this.isStreaming) return;
      const history = this.messages
        .filter((message) => message.text)
        .slice(-6)
        .map((message) => ({
          role: message.role === "assistant" ? "assistant" : "user",
          content: message.text,
        }));
      this.lastQuestion = question;
      this.messages.push({ role: "user", text: question, streaming: false });
      this.messages.push({
        role: "assistant",
        text: "",
        html: "",
        streaming: true,
        shownLength: 0,
        tools: [],
      });
      this.error = "";
      this.draft = "";
      this.pinned = true;
      this.$nextTick(() => {
        this.growInput();
        this.measureLift();
        this.followLatest(true);
      });
      this.socket.send(JSON.stringify({ question, history }));
    },

    stop() {
      if (!this.socket) return;
      const current = this.currentAssistant();
      if (current) {
        current.streaming = false;
        current.stopped = true;
        this.renderMessage(current, { animate: false, highlight: Boolean(current.text) });
      }
      this.socket.send(JSON.stringify({ type: "stop" }));
    },

    retryLast() {
      if (!this.lastQuestion || this.isStreaming) return;
      this.ask(this.lastQuestion);
    },

    onEvent(payload) {
      const current = this.currentAssistant();
      if (payload.type === "start") {
        this.error = "";
        return;
      }
      if (payload.type === "stopped") {
        return;
      }
      if (!current) return;
      if (payload.type === "token") {
        current.text += payload.text || "";
        this.scheduleRender();
      } else if (payload.type === "tool") {
        current.tools = current.tools || [];
        current.tools.push(payload.name);
      } else if (payload.type === "end") {
        current.streaming = false;
        this.renderMessage(current, { animate: false, highlight: true });
        this.followLatest();
      } else if (payload.type === "error") {
        current.streaming = false;
        this.error = payload.message || "Помилка";
      }
    },

    currentAssistant() {
      for (let index = this.messages.length - 1; index >= 0; index -= 1) {
        if (this.messages[index].role === "assistant" && this.messages[index].streaming) {
          return this.messages[index];
        }
      }
      return null;
    },

    scheduleRender() {
      if (this.renderFrame) return;
      this.renderFrame = window.requestAnimationFrame(() => {
        this.renderFrame = 0;
        const current = this.currentAssistant();
        if (current) {
          this.renderMessage(current, { animate: true, highlight: false });
          this.followLatest();
        }
      });
    },

    render(message) {
      return message.html || "";
    },

    renderMessage(message, options = {}) {
      const animate = options.animate !== false;
      const parsed = window.marked.parse(message.text || "", { breaks: true, gfm: true });
      const clean = window.DOMPurify.sanitize(parsed);
      const root = document.createElement("div");
      root.innerHTML = clean;
      wrapTables(root);
      const nextLength = textLength(root);
      if (animate && nextLength > (message.shownLength || 0)) {
        wrapNewTokens(root, message.shownLength || 0);
      }
      message.shownLength = nextLength;
      const caret = message.streaming ? '<span class="caret"></span>' : "";
      message.html = root.innerHTML + caret;
      this.$nextTick(() => {
        if (options.highlight) this.highlight(message);
      });
    },

    highlight(message) {
      const index = this.messages.indexOf(message);
      const scope = this.$root.querySelector(`.msg[data-index="${index}"] .md`);
      if (!scope) return;
      scope.querySelectorAll("pre code").forEach((block) => {
        if (block.dataset.highlighted === "yes") return;
        if (window.hljs) window.hljs.highlightElement(block);
        block.dataset.highlighted = "yes";
        const pre = block.parentElement;
        if (!pre || pre.querySelector(".code-head")) return;
        const lang = languageLabel(block);
        const head = document.createElement("div");
        head.className = "code-head";
        const label = document.createElement("span");
        label.textContent = lang;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "copy-code";
        button.textContent = "Копіювати";
        button.addEventListener("click", async () => {
          await copyText(block.innerText);
          button.textContent = "Скопійовано";
          window.setTimeout(() => {
            button.textContent = "Копіювати";
          }, 1500);
        });
        head.append(label, button);
        pre.prepend(head);
      });
    },

    onFeedScroll() {
      const feed = this.$refs.feed;
      if (!feed) return;
      this.pinned = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 80;
    },

    followLatest(force) {
      const feed = this.$refs.feed;
      if (!feed || (!this.pinned && !force)) return;
      feed.scrollTop = feed.scrollHeight;
    },

    jumpToLatest() {
      this.pinned = true;
      this.followLatest(true);
    },

    toolLabel(message) {
      if (message.tools && message.tools.length) return "Перевіряю програму…";
      return "Думаю…";
    },
  };
}

function textLength(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let length = 0;
  while (walker.nextNode()) length += walker.currentNode.textContent.length;
  return length;
}

function wrapTables(root) {
  root.querySelectorAll("table").forEach((table) => {
    if (table.parentElement && table.parentElement.classList.contains("table-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    table.replaceWith(wrap);
    wrap.appendChild(table);
  });
}

function wrapNewTokens(root, prevLen) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  let remaining = Math.max(0, textLength(root) - prevLen);
  for (let index = nodes.length - 1; index >= 0 && remaining > 0; index -= 1) {
    const node = nodes[index];
    const text = node.textContent;
    const take = Math.min(text.length, remaining);
    if (!take || !node.parentNode) continue;
    remaining -= take;
    if (node.parentElement && node.parentElement.closest("pre")) continue;
    const splitAt = text.length - take;
    const span = document.createElement("span");
    span.className = "tok";
    if (splitAt === 0) {
      span.textContent = text;
      node.parentNode.replaceChild(span, node);
    } else {
      node.textContent = text.slice(0, splitAt);
      span.textContent = text.slice(splitAt);
      node.parentNode.insertBefore(span, node.nextSibling);
    }
  }
}

function languageLabel(block) {
  const match = [...block.classList].find((name) => name.startsWith("language-"));
  if (!match) return "код";
  return match.replace("language-", "");
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}
