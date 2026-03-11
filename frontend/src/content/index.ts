// Content Script for Agent Skill Extension
// Runs on all pages to enable page content extraction

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "EXTRACT_CONTENT") {
    const title = document.title;
    const url = window.location.href;

    // Extract main text content, removing scripts and styles
    const clone = document.body.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("script, style, noscript, iframe").forEach((el) => el.remove());
    const text = clone.innerText.replace(/\s+/g, " ").trim().slice(0, 4000);

    // Extract meta description
    const metaDesc = document.querySelector('meta[name="description"]')?.getAttribute("content") || "";

    sendResponse({
      title,
      url,
      description: metaDesc,
      content: text,
      extractedAt: new Date().toISOString(),
    });
  }
});

console.log("Agent Skill Extension content script loaded");
