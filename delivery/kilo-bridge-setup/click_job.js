(() => {
  const links = Array.from(document.querySelectorAll("a"));
  for (const link of links) {
    if (link.href && link.href.includes("/job-apply") && link.textContent.includes("GenAI Architect")) {
      link.click();
      return {clicked: true, href: link.href};
    }
  }
  for (const link of links) {
    if (link.textContent.includes("GenAI Architect") && link.href) {
      link.click();
      return {clicked: true, href: link.href, fallback: true};
    }
  }
  return {clicked: false, count: links.length};
})()