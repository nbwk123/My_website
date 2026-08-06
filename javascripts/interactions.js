(() => {
  const supportsFinePointer = window.matchMedia("(pointer: fine)").matches;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!supportsFinePointer || prefersReducedMotion) {
    return;
  }

  const cursorLight = document.querySelector(".cursor-light");
  let cursorX = window.innerWidth / 2;
  let cursorY = window.innerHeight / 2;
  let lightX = cursorX;
  let lightY = cursorY;

  const moveLight = () => {
    lightX += (cursorX - lightX) * 0.18;
    lightY += (cursorY - lightY) * 0.18;

    if (cursorLight) {
      cursorLight.style.transform = `translate3d(${lightX}px, ${lightY}px, 0)`;
    }

    requestAnimationFrame(moveLight);
  };

  window.addEventListener("pointermove", (event) => {
    cursorX = event.clientX;
    cursorY = event.clientY;
    document.documentElement.style.setProperty("--cursor-x", `${event.clientX}px`);
    document.documentElement.style.setProperty("--cursor-y", `${event.clientY}px`);
  });

  moveLight();

  document.querySelectorAll("[data-tilt]").forEach((card) => {
    card.addEventListener("pointermove", (event) => {
      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const rotateX = ((y / rect.height) - 0.5) * -5;
      const rotateY = ((x / rect.width) - 0.5) * 5;

      card.style.setProperty("--tilt-x", `${rotateX}deg`);
      card.style.setProperty("--tilt-y", `${rotateY}deg`);
      card.style.setProperty("--shine-x", `${x}px`);
      card.style.setProperty("--shine-y", `${y}px`);
    });

    card.addEventListener("pointerleave", () => {
      card.style.setProperty("--tilt-x", "0deg");
      card.style.setProperty("--tilt-y", "0deg");
      card.style.setProperty("--shine-x", "50%");
      card.style.setProperty("--shine-y", "50%");
    });
  });
})();

(() => {
  document.querySelectorAll("[data-card-stack]").forEach((stack) => {
    let activeCard = null;
    let startX = 0;
    let startY = 0;
    let dragX = 0;
    let dragY = 0;

    stack.querySelectorAll(".home-visual-card, .home-visual-card img").forEach((element) => {
      element.setAttribute("draggable", "false");
    });

    const resetDrag = (card) => {
      card.style.setProperty("--drag-x", "0px");
      card.style.setProperty("--drag-y", "0px");
      card.style.setProperty("--drag-rotate", "0deg");
      card.classList.remove("is-dragging");
    };

    const cycleCard = (card, direction) => {
      card.classList.add("is-exiting");
      card.style.setProperty("--drag-x", `${direction * 230}px`);
      card.style.setProperty("--drag-y", `${dragY * 0.16}px`);
      card.style.setProperty("--drag-rotate", `${direction * 7}deg`);

      window.setTimeout(() => {
        stack.append(card);
        card.classList.add("is-dragging");
        resetDrag(card);

        window.requestAnimationFrame(() => {
          card.classList.remove("is-exiting");
        });
      }, 250);
    };

    const finishDrag = (event) => {
      if (!activeCard) {
        return;
      }

      const releasedCard = activeCard;
      const shouldCycle = Math.abs(dragX) > 74 || Math.abs(dragY) > 72;
      const direction = dragX >= 0 ? 1 : -1;

      if (releasedCard.hasPointerCapture(event.pointerId)) {
        releasedCard.releasePointerCapture(event.pointerId);
      }

      releasedCard.classList.remove("is-dragging");
      activeCard = null;

      if (shouldCycle) {
        releasedCard.dataset.skipClick = "true";
        cycleCard(releasedCard, direction);
      } else {
        resetDrag(releasedCard);
      }
    };

    stack.addEventListener("pointerdown", (event) => {
      const topCard = stack.querySelector(".home-visual-card:first-child");

      if (!topCard || !topCard.contains(event.target)) {
        return;
      }

      event.preventDefault();
      activeCard = topCard;
      startX = event.clientX;
      startY = event.clientY;
      dragX = 0;
      dragY = 0;
      activeCard.dataset.skipClick = "false";
      activeCard.classList.add("is-dragging");
      activeCard.setPointerCapture(event.pointerId);
    });

    stack.addEventListener("pointermove", (event) => {
      if (!activeCard) {
        return;
      }

      event.preventDefault();
      dragX = event.clientX - startX;
      dragY = event.clientY - startY;
      activeCard.style.setProperty("--drag-x", `${dragX}px`);
      activeCard.style.setProperty("--drag-y", `${dragY}px`);
      activeCard.style.setProperty("--drag-rotate", `${dragX / 24}deg`);

      if (Math.abs(dragX) > 6 || Math.abs(dragY) > 6) {
        activeCard.dataset.skipClick = "true";
      }
    });

    stack.addEventListener("pointerup", finishDrag);
    stack.addEventListener("pointercancel", finishDrag);

    stack.addEventListener(
      "click",
      (event) => {
        const card = event.target.closest(".home-visual-card");

        if (card?.dataset.skipClick === "true") {
          event.preventDefault();
          card.dataset.skipClick = "false";
        }
      },
      true
    );
  });
})();

(() => {
  const isSearchInput = (target) => target instanceof HTMLInputElement && target.matches(".md-search__input");
  let searchDocsPromise;
  let latestSearchRender = 0;

  const getSiteBase = () => {
    const configNode = document.getElementById("__config");
    const fallback = new URL("./", window.location.href);

    if (!configNode) {
      return fallback;
    }

    try {
      const config = JSON.parse(configNode.textContent || "{}");
      return new URL(`${config.base || "."}/`, window.location.href);
    } catch {
      return fallback;
    }
  };

  const stripHtml = (value) => {
    const template = document.createElement("template");
    template.innerHTML = value || "";
    return (template.content.textContent || "").replace(/\s+/g, " ").trim();
  };

  const getSearchDocs = () => {
    if (!searchDocsPromise) {
      searchDocsPromise = fetch(new URL("search/search_index.json", getSiteBase()))
        .then((response) => response.json())
        .then((index) => index.docs || [])
        .catch(() => []);
    }

    return searchDocsPromise;
  };

  const getSearchPanel = (input) => {
    const wrap = input.closest(".site-topbar__search-wrap");
    return wrap?.querySelector("[data-site-search-results]");
  };

  const getSearchCopy = () => {
    const isEnglish = window.location.pathname.includes("/en/");

    return {
      empty: isEnglish ? "Type a keyword to see results" : "输入关键词后显示搜索结果",
      none: isEnglish ? "No results found" : "没有找到相关结果",
      unnamed: isEnglish ? "Untitled page" : "未命名页面",
      found: (count) => (isEnglish ? `${count} related result${count > 1 ? "s" : ""}` : `找到 ${count} 个相关结果`),
    };
  };

  const isEnglishPage = () => window.location.pathname.includes("/en/");

  const isCurrentLanguageDoc = (doc) => {
    const location = doc.location || "";
    return isEnglishPage() ? location.startsWith("en/") : !location.startsWith("en/");
  };

  const createExcerpt = (text, query) => {
    const normalizedText = text.toLowerCase();
    const index = normalizedText.indexOf(query);

    if (index === -1) {
      return text.slice(0, 52);
    }

    const lead = 10;
    const length = 54;
    const start = Math.max(0, index - lead);
    const end = Math.min(text.length, start + length);
    const prefix = start > 0 && lead > 0 ? "..." : "";
    const suffix = end < text.length ? "..." : "";

    return `${prefix}${text.slice(start, end)}${suffix}`;
  };

  const appendHighlightedText = (node, text, query) => {
    const lowerText = text.toLowerCase();
    let cursor = 0;
    let index = lowerText.indexOf(query, cursor);

    while (index !== -1) {
      if (index > cursor) {
        node.append(document.createTextNode(text.slice(cursor, index)));
      }

      const mark = document.createElement("mark");
      mark.className = "site-search-results__highlight";
      mark.textContent = text.slice(index, index + query.length);
      node.append(mark);

      cursor = index + query.length;
      index = lowerText.indexOf(query, cursor);
    }

    if (cursor < text.length) {
      node.append(document.createTextNode(text.slice(cursor)));
    }
  };

  const renderSearchResults = async (input) => {
    const renderId = ++latestSearchRender;
    const panel = getSearchPanel(input);
    const meta = panel?.querySelector(".site-search-results__meta");
    const list = panel?.querySelector(".site-search-results__list");
    const query = input.value.trim().toLowerCase();
    const copy = getSearchCopy();

    if (!panel || !meta || !list) {
      return;
    }

    list.innerHTML = "";

    if (!query) {
      panel.hidden = true;
      meta.textContent = copy.empty;
      return;
    }

    panel.hidden = false;

    const siteBase = getSiteBase();
    const docs = await getSearchDocs();

    if (renderId !== latestSearchRender) {
      return;
    }

    const matches = docs
      .filter(isCurrentLanguageDoc)
      .map((doc) => {
        const title = stripHtml(doc.title);
        const text = stripHtml(doc.text);
        const haystack = `${title} ${text}`.toLowerCase();

        if (!haystack.includes(query)) {
          return null;
        }

        const titleHit = title.toLowerCase().includes(query);
        const excerpt = createExcerpt(text, query);

        return { ...doc, title, text, excerpt, score: titleHit ? 2 : 1 };
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8);

    meta.textContent = matches.length ? copy.found(matches.length) : copy.none;

    matches.forEach((doc) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      const title = document.createElement("h3");
      const excerpt = document.createElement("p");

      item.className = "site-search-results__item";
      link.className = "site-search-results__link";
      link.href = new URL(doc.location || "", siteBase).toString();
      title.className = "site-search-results__title";
      appendHighlightedText(title, doc.title || copy.unnamed, query);
      excerpt.className = "site-search-results__excerpt";
      appendHighlightedText(excerpt, doc.excerpt || doc.text || "", query);

      link.append(title, excerpt);
      item.append(link);
      list.append(item);
    });
  };

  const scheduleSearchResults = (input) => {
    window.setTimeout(() => renderSearchResults(input), 80);
  };

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Enter" || !isSearchInput(event.target)) {
        return;
      }

      event.preventDefault();
      event.stopImmediatePropagation();
    },
    true
  );

  document.addEventListener("input", (event) => {
    if (isSearchInput(event.target)) {
      scheduleSearchResults(event.target);
    }
  });

  document.addEventListener("focusin", (event) => {
    if (isSearchInput(event.target)) {
      scheduleSearchResults(event.target);
    }
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest(".site-topbar__search-wrap")) {
      return;
    }

    document.querySelectorAll("[data-site-search-results]").forEach((panel) => {
      panel.hidden = true;
    });
  });

  document.addEventListener(
    "submit",
    (event) => {
      if (!(event.target instanceof HTMLFormElement) || !event.target.matches(".md-search__form")) {
        return;
      }

      event.preventDefault();
      event.stopImmediatePropagation();
    },
    true
  );
})();
