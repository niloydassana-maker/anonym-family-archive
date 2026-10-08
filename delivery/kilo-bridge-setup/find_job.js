(() => {
  const els = Array.from(document.querySelectorAll("*"));
  const matches = els.filter(el => el.textContent && el.textContent.includes("GenAI Architect") && el.textContent.includes("Generative AI"));
  return matches.map(m => ({tag: m.tagName, class: m.className, id: m.id, onclick: m.onclick ? true : false, href: m.href, role: m.getAttribute("role"), tabindex: m.tabIndex, text: m.textContent.slice(0,120)}));
})()