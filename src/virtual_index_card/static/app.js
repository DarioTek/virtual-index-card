const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
const createForm = document.getElementById('create-form');
const selectedDeckId =
  createForm?.dataset.deckId || document.querySelector('.review-stage')?.dataset.deckId;
const deckQuery = selectedDeckId ? `?deck_id=${encodeURIComponent(selectedDeckId)}` : '';

const MAX_VISIBLE_CHARS = 5000;
const PALETTE_COLORS = new Set(['black', 'green', 'red', 'orange', 'blue', 'pink']);
const richFieldControllers = new WeakMap();

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) message = body.detail;
    } catch (_) {
      // Keep the generic message.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function showError(element, message) {
  if (!element) {
    window.alert(message);
    return;
  }
  element.textContent = message;
  element.hidden = false;
}

function clearError(element) {
  if (!element) return;
  element.textContent = '';
  element.hidden = true;
}

function reloadAfter(promise, errorElement = null) {
  clearError(errorElement);
  promise
    .then(() => window.location.reload())
    .catch((error) => showError(errorElement, error.message));
}

// --- Rich-text formatting model & editor ----------------------------------

function cloneDoc(doc) {
  return {
    version: 1,
    blocks: doc.blocks.map((block) => ({
      type: block.type === 'blockquote' ? 'blockquote' : 'paragraph',
      runs: block.runs.map((run) => ({
        text: String(run.text || ''),
        bold: Boolean(run.bold),
        italic: Boolean(run.italic),
        underline: Boolean(run.underline),
        color: PALETTE_COLORS.has(run.color) ? run.color : null,
      })),
    })),
  };
}

function plainTextToDoc(text) {
  const normalized = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = normalized.split('\n');
  return {
    version: 1,
    blocks: lines.map((line) => ({
      type: 'paragraph',
      runs: line ? [{ text: line, bold: false, italic: false, underline: false, color: null }] : [],
    })),
  };
}

function docToPlainText(doc) {
  return doc.blocks
    .map((block) => block.runs.map((run) => run.text).join(''))
    .join('\n');
}

function hasAnyFormatting(doc) {
  return doc.blocks.some(
    (block) =>
      block.type !== 'paragraph' ||
      block.runs.some((run) => run.bold || run.italic || run.underline || run.color)
  );
}

function canonicalizeForPayload(doc) {
  if (!hasAnyFormatting(doc)) return null;
  return {
    version: 1,
    blocks: doc.blocks.map((block) => ({
      type: block.type,
      runs: block.runs
        .filter((run) => run.text.length > 0)
        .map((run) => {
          const entry = { text: run.text };
          if (run.bold) entry.bold = true;
          if (run.italic) entry.italic = true;
          if (run.underline) entry.underline = true;
          if (run.color) entry.color = run.color;
          return entry;
        }),
    })),
  };
}

function styleKey(run) {
  return `${run.bold ? 1 : 0}:${run.italic ? 1 : 0}:${run.underline ? 1 : 0}:${run.color || ''}`;
}

function mergeAdjacentRuns(runs) {
  const merged = [];
  for (const run of runs) {
    if (!run.text) continue;
    const prev = merged[merged.length - 1];
    if (prev && styleKey(prev) === styleKey(run)) {
      prev.text += run.text;
    } else {
      merged.push({ ...run });
    }
  }
  return merged;
}

function codePointLength(text) {
  return Array.from(text).length;
}

function trimmedPlainLength(text) {
  return codePointLength(text.trim());
}

function readInlineStyles(node, inherited) {
  if (!(node instanceof Element)) return inherited;
  const tag = node.tagName;
  const next = { ...inherited };
  if (tag === 'B' || tag === 'STRONG' || node.dataset.bold === '1') next.bold = true;
  if (tag === 'I' || tag === 'EM' || node.dataset.italic === '1') next.italic = true;
  if (tag === 'U' || node.dataset.underline === '1') next.underline = true;
  if (node.dataset.color && PALETTE_COLORS.has(node.dataset.color)) {
    next.color = node.dataset.color;
  }
  return next;
}

function collectRunsFromNode(node, inherited, currentRuns, extraBlocks, blockType) {
  if (node.nodeType === Node.TEXT_NODE) {
    const raw = (node.nodeValue || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const parts = raw.split('\n');
    for (let index = 0; index < parts.length; index += 1) {
      if (index > 0) {
        extraBlocks.push({ type: blockType, runs: mergeAdjacentRuns(currentRuns.splice(0)) });
      }
      if (parts[index]) {
        currentRuns.push({ text: parts[index], ...inherited });
      }
    }
    return;
  }
  if (!(node instanceof Element)) return;
  if (node.tagName === 'BR') {
    const isPlaceholderOnly =
      currentRuns.length === 0 &&
      !node.previousSibling &&
      !node.nextSibling;
    if (!isPlaceholderOnly) {
      extraBlocks.push({ type: blockType, runs: mergeAdjacentRuns(currentRuns.splice(0)) });
    }
    return;
  }
  const styles = readInlineStyles(node, inherited);
  for (const child of node.childNodes) {
    collectRunsFromNode(child, styles, currentRuns, extraBlocks, blockType);
  }
}

function parseEditorToDoc(editor) {
  const blocks = [];
  const defaultStyle = { bold: false, italic: false, underline: false, color: null };
  let orphanRuns = [];

  function flushOrphan() {
    if (orphanRuns.length > 0) {
      blocks.push({ type: 'paragraph', runs: mergeAdjacentRuns(orphanRuns) });
      orphanRuns = [];
    }
  }

  for (const child of editor.childNodes) {
    if (child.nodeType === Node.ELEMENT_NODE) {
      const tag = child.tagName;
      if (tag === 'P' || tag === 'DIV' || tag === 'BLOCKQUOTE') {
        flushOrphan();
        const blockType =
          tag === 'BLOCKQUOTE' || child.dataset.blockType === 'blockquote'
            ? 'blockquote'
            : 'paragraph';
        const runs = [];
        const nestedBlocks = [];
        for (const inner of child.childNodes) {
          collectRunsFromNode(inner, defaultStyle, runs, nestedBlocks, blockType);
        }
        for (const nb of nestedBlocks) {
          blocks.push(nb);
        }
        blocks.push({ type: blockType, runs: mergeAdjacentRuns(runs) });
        continue;
      }
      if (tag === 'BR') {
        flushOrphan();
        blocks.push({ type: 'paragraph', runs: [] });
        continue;
      }
    }
    const extra = [];
    collectRunsFromNode(child, defaultStyle, orphanRuns, extra, 'paragraph');
    for (const eb of extra) {
      blocks.push(eb);
    }
  }
  flushOrphan();

  if (blocks.length === 0) {
    blocks.push({ type: 'paragraph', runs: [] });
  }
  return { version: 1, blocks };
}

function renderDocToEditor(editor, doc) {
  const fragment = document.createDocumentFragment();
  for (const block of doc.blocks) {
    const tag = block.type === 'blockquote' ? 'blockquote' : 'p';
    const blockEl = document.createElement(tag);
    blockEl.className = 'fmt-editor-block';
    blockEl.dataset.blockType = block.type;
    if (block.runs.length === 0) {
      blockEl.appendChild(document.createElement('br'));
    } else {
      for (const run of block.runs) {
        const span = document.createElement('span');
        if (run.bold) {
          span.dataset.bold = '1';
          span.classList.add('fmt-bold');
        }
        if (run.italic) {
          span.dataset.italic = '1';
          span.classList.add('fmt-italic');
        }
        if (run.underline) {
          span.dataset.underline = '1';
          span.classList.add('fmt-underline');
        }
        if (run.color && PALETTE_COLORS.has(run.color)) {
          span.dataset.color = run.color;
          span.classList.add(`fmt-color-${run.color}`);
        }
        span.appendChild(document.createTextNode(run.text));
        blockEl.appendChild(span);
      }
    }
    fragment.appendChild(blockEl);
  }
  editor.replaceChildren(fragment);
}

function resolveEditorPoint(editor, container, offset) {
  const blocks = Array.from(editor.children);
  if (blocks.length === 0) return { blockIndex: 0, charOffset: 0 };

  if (container === editor) {
    const clampedIndex = Math.min(offset, blocks.length - 1);
    if (offset >= blocks.length) {
      const last = blocks[blocks.length - 1];
      return { blockIndex: blocks.length - 1, charOffset: (last.textContent || '').length };
    }
    return { blockIndex: clampedIndex, charOffset: 0 };
  }

  let blockEl = container.nodeType === Node.ELEMENT_NODE ? container : container.parentElement;
  while (blockEl && blockEl.parentElement !== editor) {
    blockEl = blockEl.parentElement;
  }
  const blockIndex = Math.max(0, blocks.indexOf(blockEl));
  const targetBlock = blocks[blockIndex];
  if (!targetBlock) return { blockIndex: 0, charOffset: 0 };

  const range = document.createRange();
  range.selectNodeContents(targetBlock);
  range.setEnd(container, offset);
  return { blockIndex, charOffset: range.toString().length };
}

function getEditorSelection(editor) {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  if (!editor.contains(range.startContainer) || !editor.contains(range.endContainer)) {
    return null;
  }
  const start = resolveEditorPoint(editor, range.startContainer, range.startOffset);
  const end = resolveEditorPoint(editor, range.endContainer, range.endOffset);
  if (
    start.blockIndex > end.blockIndex ||
    (start.blockIndex === end.blockIndex && start.charOffset > end.charOffset)
  ) {
    return {
      startBlock: end.blockIndex,
      startOffset: end.charOffset,
      endBlock: start.blockIndex,
      endOffset: start.charOffset,
    };
  }
  return {
    startBlock: start.blockIndex,
    startOffset: start.charOffset,
    endBlock: end.blockIndex,
    endOffset: end.charOffset,
  };
}

function findPointInBlock(blockEl, targetOffset) {
  let remaining = targetOffset;
  const walker = document.createTreeWalker(blockEl, NodeFilter.SHOW_TEXT);
  let textNode = walker.nextNode();
  let lastText = null;
  while (textNode) {
    lastText = textNode;
    const len = (textNode.nodeValue || '').length;
    if (remaining <= len) {
      return { node: textNode, offset: remaining };
    }
    remaining -= len;
    textNode = walker.nextNode();
  }
  if (lastText) {
    return { node: lastText, offset: (lastText.nodeValue || '').length };
  }
  return { node: blockEl, offset: 0 };
}

function setEditorSelection(editor, sel) {
  const blocks = Array.from(editor.children);
  if (blocks.length === 0) return;
  const startBlockEl = blocks[Math.min(sel.startBlock, blocks.length - 1)];
  const endBlockEl = blocks[Math.min(sel.endBlock, blocks.length - 1)];
  const startPoint = findPointInBlock(startBlockEl, sel.startOffset);
  const endPoint = findPointInBlock(endBlockEl, sel.endOffset);

  const range = document.createRange();
  range.setStart(startPoint.node, startPoint.offset);
  range.setEnd(endPoint.node, endPoint.offset);
  const selection = window.getSelection();
  if (selection) {
    selection.removeAllRanges();
    selection.addRange(range);
  }
}

function splitBlockRunsAtSelection(runs, selStart, selEnd) {
  const segments = [];
  let cursor = 0;
  for (const run of runs) {
    const len = run.text.length;
    const runStart = cursor;
    const runEnd = cursor + len;
    cursor = runEnd;

    if (len === 0) continue;
    const cutPoints = [runStart];
    if (selStart > runStart && selStart < runEnd) cutPoints.push(selStart);
    if (selEnd > runStart && selEnd < runEnd && selEnd !== selStart) cutPoints.push(selEnd);
    cutPoints.push(runEnd);

    for (let i = 0; i < cutPoints.length - 1; i += 1) {
      const a = cutPoints[i];
      const b = cutPoints[i + 1];
      const slice = run.text.slice(a - runStart, b - runStart);
      const selected = a >= selStart && b <= selEnd;
      segments.push({
        run: { ...run, text: slice },
        selected,
      });
    }
  }
  return segments;
}

function getCaretStyles(doc, blockIndex, charOffset) {
  const block = doc.blocks[blockIndex];
  const empty = { bold: false, italic: false, underline: false, color: null };
  if (!block || block.runs.length === 0) return empty;
  let cursor = 0;
  for (const run of block.runs) {
    const end = cursor + run.text.length;
    if (charOffset > cursor && charOffset <= end) {
      return {
        bold: Boolean(run.bold),
        italic: Boolean(run.italic),
        underline: Boolean(run.underline),
        color: run.color || null,
      };
    }
    if (charOffset === 0 && cursor === 0) {
      return {
        bold: Boolean(run.bold),
        italic: Boolean(run.italic),
        underline: Boolean(run.underline),
        color: run.color || null,
      };
    }
    cursor = end;
  }
  const last = block.runs[block.runs.length - 1];
  return {
    bold: Boolean(last.bold),
    italic: Boolean(last.italic),
    underline: Boolean(last.underline),
    color: last.color || null,
  };
}

function inspectSelectionFormats(doc, sel, pendingStyles) {
  const active = {
    bold: false,
    italic: false,
    underline: false,
    blockquote: false,
    color: null,
  };
  if (!sel || doc.blocks.length === 0) return active;

  const startB = Math.min(sel.startBlock, doc.blocks.length - 1);
  const endB = Math.min(sel.endBlock, doc.blocks.length - 1);
  active.blockquote = doc.blocks
    .slice(startB, endB + 1)
    .every((block) => block.type === 'blockquote');

  if (startB === endB && sel.startOffset === sel.endOffset) {
    const styles = pendingStyles || getCaretStyles(doc, startB, sel.startOffset);
    return { ...active, ...styles };
  }

  const selectedRuns = [];
  for (let b = startB; b <= endB; b += 1) {
    const blockTextLen = doc.blocks[b].runs.reduce((sum, r) => sum + r.text.length, 0);
    const s = b === startB ? sel.startOffset : 0;
    const e = b === endB ? sel.endOffset : blockTextLen;
    for (const seg of splitBlockRunsAtSelection(doc.blocks[b].runs, s, e)) {
      if (seg.selected && seg.run.text.length > 0) {
        selectedRuns.push(seg.run);
      }
    }
  }
  if (selectedRuns.length === 0) return active;

  active.bold = selectedRuns.every((r) => r.bold);
  active.italic = selectedRuns.every((r) => r.italic);
  active.underline = selectedRuns.every((r) => r.underline);
  const firstColor = selectedRuns[0].color || null;
  if (firstColor && selectedRuns.every((r) => (r.color || null) === firstColor)) {
    active.color = firstColor;
  }
  return active;
}

function spliceTextInDoc(doc, sel, insertedText, styles) {
  const next = cloneDoc(doc);
  const startB = Math.min(sel.startBlock, next.blocks.length - 1);
  const endB = Math.min(sel.endBlock, next.blocks.length - 1);

  const beforeRuns = [];
  const afterRuns = [];
  const startLen = next.blocks[startB].runs.reduce((s, r) => s + r.text.length, 0);
  const endLen = next.blocks[endB].runs.reduce((s, r) => s + r.text.length, 0);

  for (const seg of splitBlockRunsAtSelection(next.blocks[startB].runs, 0, sel.startOffset)) {
    if (seg.selected) beforeRuns.push(seg.run);
  }
  for (const seg of splitBlockRunsAtSelection(next.blocks[endB].runs, sel.endOffset, endLen)) {
    if (seg.selected) afterRuns.push(seg.run);
  }
  // Keep unused reference silenced: startLen confirms valid range.
  void startLen;

  const baseType = next.blocks[startB].type;
  const lines = insertedText.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const insertedBlocks = [];
  for (let i = 0; i < lines.length; i += 1) {
    const runs = [];
    if (i === 0) runs.push(...beforeRuns);
    if (lines[i]) {
      runs.push({
        text: lines[i],
        bold: Boolean(styles.bold),
        italic: Boolean(styles.italic),
        underline: Boolean(styles.underline),
        color: styles.color || null,
      });
    }
    if (i === lines.length - 1) runs.push(...afterRuns);
    insertedBlocks.push({ type: baseType, runs: mergeAdjacentRuns(runs) });
  }

  next.blocks.splice(startB, endB - startB + 1, ...insertedBlocks);
  const caretBlock = startB + lines.length - 1;
  const caretOffset =
    (lines.length === 1 ? sel.startOffset : 0) + lines[lines.length - 1].length;
  return {
    doc: next,
    selection: {
      startBlock: caretBlock,
      startOffset: caretOffset,
      endBlock: caretBlock,
      endOffset: caretOffset,
    },
  };
}

function hydrateRichField(fieldEl) {
  const textarea = fieldEl.querySelector('textarea');
  const toolbar = fieldEl.querySelector('.fmt-toolbar');
  const editor = fieldEl.querySelector('.rich-editor');
  const counter = fieldEl.querySelector('.char-counter');
  const initialScript = fieldEl.querySelector('.initial-rich-doc');
  if (!textarea || !toolbar || !editor) return null;

  let initialDoc;
  if (initialScript && initialScript.textContent.trim()) {
    try {
      initialDoc = cloneDoc(JSON.parse(initialScript.textContent));
    } catch (_) {
      initialDoc = plainTextToDoc(textarea.value);
    }
  } else {
    initialDoc = plainTextToDoc(textarea.value);
  }

  let currentDoc = cloneDoc(initialDoc);
  let lastSelection = { startBlock: 0, startOffset: 0, endBlock: 0, endOffset: 0 };
  let pendingStyles = null;
  let isComposing = false;

  textarea.hidden = true;
  textarea.required = false;
  toolbar.hidden = false;
  editor.hidden = false;

  function syncMetadata() {
    const plain = docToPlainText(currentDoc);
    textarea.value = plain;
    const count = trimmedPlainLength(plain);
    if (counter) {
      counter.textContent = `${count.toLocaleString()} / ${MAX_VISIBLE_CHARS.toLocaleString()}`;
      counter.classList.toggle('is-over-limit', count > MAX_VISIBLE_CHARS);
    }
    editor.classList.toggle('is-empty', plain.length === 0);
  }

  function updateToolbarState() {
    const active = inspectSelectionFormats(currentDoc, lastSelection, pendingStyles);
    toolbar.querySelectorAll('.fmt-btn').forEach((btn) => {
      if (btn.dataset.command) {
        btn.setAttribute('aria-pressed', String(Boolean(active[btn.dataset.command])));
      } else if (btn.dataset.color) {
        btn.setAttribute('aria-pressed', String(active.color === btn.dataset.color));
      }
    });
  }

  function selectionsEqual(a, b) {
    return (
      a.startBlock === b.startBlock &&
      a.startOffset === b.startOffset &&
      a.endBlock === b.endBlock &&
      a.endOffset === b.endOffset
    );
  }

  function captureSelection() {
    const sel = getEditorSelection(editor);
    if (sel) {
      if (!selectionsEqual(sel, lastSelection)) {
        pendingStyles = null;
      }
      lastSelection = sel;
      updateToolbarState();
    }
  }

  function commitDoc(nextDoc, nextSelection, restoreFocus = false) {
    currentDoc = nextDoc;
    lastSelection = nextSelection;
    renderDocToEditor(editor, currentDoc);
    syncMetadata();
    if (restoreFocus) {
      editor.focus();
    }
    if (document.activeElement === editor) {
      setEditorSelection(editor, lastSelection);
    }
    updateToolbarState();
  }

  function applyCommand(command, colorValue = null, restoreFocus = false) {
    const sel = getEditorSelection(editor) || lastSelection;
    const next = cloneDoc(currentDoc);
    const startB = Math.min(sel.startBlock, next.blocks.length - 1);
    const endB = Math.min(sel.endBlock, next.blocks.length - 1);

    if (command === 'blockquote') {
      const allQuoted = next.blocks
        .slice(startB, endB + 1)
        .every((block) => block.type === 'blockquote');
      const targetType = allQuoted ? 'paragraph' : 'blockquote';
      for (let b = startB; b <= endB; b += 1) {
        next.blocks[b].type = targetType;
      }
      commitDoc(next, sel, restoreFocus);
      return;
    }

    const isCollapsed = startB === endB && sel.startOffset === sel.endOffset;
    if (isCollapsed) {
      const base = pendingStyles || getCaretStyles(currentDoc, startB, sel.startOffset);
      const updated = { ...base };
      if (command === 'color') {
        updated.color = updated.color === colorValue ? null : colorValue;
      } else {
        updated[command] = !updated[command];
      }
      pendingStyles = updated;
      if (restoreFocus) {
        editor.focus();
        setEditorSelection(editor, sel);
      }
      updateToolbarState();
      return;
    }

    const active = inspectSelectionFormats(next, sel, null);
    const targetBool = command === 'color' ? null : !active[command];
    const targetColor = command === 'color' ? (active.color === colorValue ? null : colorValue) : null;

    for (let b = startB; b <= endB; b += 1) {
      const block = next.blocks[b];
      const blockLen = block.runs.reduce((sum, r) => sum + r.text.length, 0);
      const sliceStart = b === startB ? sel.startOffset : 0;
      const sliceEnd = b === endB ? sel.endOffset : blockLen;
      const segments = splitBlockRunsAtSelection(block.runs, sliceStart, sliceEnd);
      block.runs = mergeAdjacentRuns(
        segments.map(({ run, selected }) => {
          if (!selected) return run;
          if (command === 'color') {
            return { ...run, color: targetColor };
          }
          return { ...run, [command]: targetBool };
        })
      );
    }

    pendingStyles = null;
    commitDoc(next, sel, restoreFocus);
  }

  renderDocToEditor(editor, currentDoc);
  syncMetadata();
  updateToolbarState();

  toolbar.addEventListener('mousedown', (event) => {
    if (event.target.closest('.fmt-btn')) {
      event.preventDefault();
    }
  });

  toolbar.addEventListener('click', (event) => {
    const btn = event.target.closest('.fmt-btn');
    if (!btn) return;
    const viaPointer = event.detail > 0;
    if (btn.dataset.command) {
      applyCommand(btn.dataset.command, null, viaPointer);
    } else if (btn.dataset.color) {
      applyCommand('color', btn.dataset.color, viaPointer);
    }
  });

  toolbar.addEventListener('keydown', (event) => {
    const buttons = Array.from(toolbar.querySelectorAll('.fmt-btn'));
    const currentIndex = buttons.indexOf(document.activeElement);
    if (currentIndex === -1) return;
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      buttons[(currentIndex + 1) % buttons.length].focus();
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      buttons[(currentIndex - 1 + buttons.length) % buttons.length].focus();
    }
  });

  editor.addEventListener('compositionstart', () => {
    isComposing = true;
  });

  editor.addEventListener('compositionend', () => {
    isComposing = false;
    currentDoc = parseEditorToDoc(editor);
    captureSelection();
    syncMetadata();
  });

  editor.addEventListener('beforeinput', (event) => {
    if (isComposing) return;
    if (event.inputType === 'insertText' && pendingStyles && typeof event.data === 'string') {
      event.preventDefault();
      const sel = getEditorSelection(editor) || lastSelection;
      const result = spliceTextInDoc(currentDoc, sel, event.data, pendingStyles);
      commitDoc(result.doc, result.selection, true);
    }
  });

  editor.addEventListener('input', () => {
    if (isComposing) return;
    currentDoc = parseEditorToDoc(editor);
    const sel = getEditorSelection(editor);
    if (sel) lastSelection = sel;
    syncMetadata();
    updateToolbarState();
  });

  editor.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && !event.altKey) {
      const key = event.key.toLowerCase();
      if (key === 'b' || key === 'i' || key === 'u') {
        event.preventDefault();
        const command = key === 'b' ? 'bold' : key === 'i' ? 'italic' : 'underline';
        applyCommand(command, null, true);
        return;
      }
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      const sel = getEditorSelection(editor) || lastSelection;
      const block = currentDoc.blocks[sel.startBlock];
      const isCollapsed = sel.startBlock === sel.endBlock && sel.startOffset === sel.endOffset;
      const isEmptyBlockquote =
        isCollapsed && block && block.type === 'blockquote' && block.runs.length === 0;
      if (isEmptyBlockquote) {
        const next = cloneDoc(currentDoc);
        next.blocks[sel.startBlock].type = 'paragraph';
        commitDoc(next, sel, true);
        return;
      }
      const styles = pendingStyles || getCaretStyles(currentDoc, sel.startBlock, sel.startOffset);
      const result = spliceTextInDoc(currentDoc, sel, '\n', styles);
      commitDoc(result.doc, result.selection, true);
    }
  });

  editor.addEventListener('paste', (event) => {
    event.preventDefault();
    const text = event.clipboardData ? event.clipboardData.getData('text/plain') : '';
    if (!text) return;
    const sel = getEditorSelection(editor) || lastSelection;
    const styles = pendingStyles || getCaretStyles(currentDoc, sel.startBlock, sel.startOffset);
    const result = spliceTextInDoc(currentDoc, sel, text, styles);
    pendingStyles = null;
    commitDoc(result.doc, result.selection, true);
  });

  editor.addEventListener('keyup', captureSelection);
  editor.addEventListener('mouseup', captureSelection);
  editor.addEventListener('focus', () => {
    const sel = getEditorSelection(editor);
    if (sel) {
      lastSelection = sel;
    } else {
      setEditorSelection(editor, lastSelection);
    }
    updateToolbarState();
  });

  const controller = {
    editor,
    captureSelection,
    getPayloadValue() {
      currentDoc = parseEditorToDoc(editor);
      const plain = docToPlainText(currentDoc);
      return {
        plain,
        rich: canonicalizeForPayload(currentDoc),
      };
    },
    reset() {
      currentDoc = cloneDoc(initialDoc);
      pendingStyles = null;
      lastSelection = { startBlock: 0, startOffset: 0, endBlock: 0, endOffset: 0 };
      renderDocToEditor(editor, currentDoc);
      syncMetadata();
      updateToolbarState();
    },
  };
  richFieldControllers.set(fieldEl, controller);
  return controller;
}

document.querySelectorAll('.rich-field').forEach((fieldEl) => {
  hydrateRichField(fieldEl);
});

function readFormCardPayload(form) {
  const frontField = form.querySelector('.rich-field[data-field-name="front"]');
  const backField = form.querySelector('.rich-field[data-field-name="back"]');
  const frontCtrl = frontField ? richFieldControllers.get(frontField) : null;
  const backCtrl = backField ? richFieldControllers.get(backField) : null;

  const frontData = frontCtrl
    ? frontCtrl.getPayloadValue()
    : { plain: form.elements.front.value, rich: null };
  const backData = backCtrl
    ? backCtrl.getPayloadValue()
    : { plain: form.elements.back.value, rich: null };

  return {
    front: frontData.plain,
    back: backData.plain,
    front_rich: frontData.rich,
    back_rich: backData.rich,
  };
}

createForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = readFormCardPayload(form);
  reloadAfter(
    apiRequest(`/api/cards${deckQuery}`, { method: 'POST', body: JSON.stringify(payload) }),
    form.querySelector('.form-error')
  );
});

document.getElementById('shuffle-btn')?.addEventListener('click', async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    await apiRequest(`/api/deck/shuffle${deckQuery}`, { method: 'POST' });
    window.location.assign(`/review${deckQuery}`);
  } catch (error) {
    button.disabled = false;
    window.alert(error.message);
  }
});

document.querySelectorAll('.edit-form').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const card = form.closest('.card');
    const payload = readFormCardPayload(form);
    reloadAfter(
      apiRequest(`/api/cards/${card.dataset.cardId}${deckQuery}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
      form.querySelector('.form-error')
    );
  });
});

document.addEventListener('click', (event) => {
  const flip = event.target.closest('.flip-button');
  if (flip) {
    const isFlipped = flip.getAttribute('aria-pressed') === 'true';
    flip.setAttribute('aria-pressed', String(!isFlipped));
    flip.closest('.card').classList.toggle('is-flipped', !isFlipped);
    return;
  }

  const edit = event.target.closest('.edit-btn');
  if (edit) {
    const card = edit.closest('.card');
    const form = card.querySelector('.edit-form');
    form.hidden = false;
    clearError(form.querySelector('.form-error'));
    card.querySelector('.flip-button').hidden = true;
    form.querySelector('.rich-editor')?.focus();
    return;
  }

  const cancel = event.target.closest('.cancel-edit');
  if (cancel) {
    const card = cancel.closest('.card');
    const form = card.querySelector('.edit-form');
    form.querySelectorAll('.rich-field').forEach((fieldEl) => {
      richFieldControllers.get(fieldEl)?.reset();
    });
    clearError(form.querySelector('.form-error'));
    form.hidden = true;
    card.querySelector('.flip-button').hidden = false;
    return;
  }

  const remove = event.target.closest('.delete-btn');
  if (remove && window.confirm('Delete this card?')) {
    const card = remove.closest('.card');
    reloadAfter(apiRequest(`/api/cards/${card.dataset.cardId}${deckQuery}`, { method: 'DELETE' }));
  }
});

document.addEventListener('selectionchange', () => {
  const activeEl = document.activeElement;
  if (!(activeEl instanceof Element)) return;
  const fieldEl = activeEl.closest('.rich-field');
  if (!fieldEl) return;
  const controller = richFieldControllers.get(fieldEl);
  if (controller && activeEl === controller.editor) {
    controller.captureSelection();
  }
});

const reviewNext = document.getElementById('review-next');
const reviewPrev = document.getElementById('review-prev');
if (reviewNext || reviewPrev) {
  document.addEventListener('keydown', (event) => {
    if (event.target.matches('input, textarea') || event.target.isContentEditable) return;
    if (event.key === 'ArrowRight' && reviewNext) reviewNext.click();
    if (event.key === 'ArrowLeft' && reviewPrev) reviewPrev.click();
  });
}
