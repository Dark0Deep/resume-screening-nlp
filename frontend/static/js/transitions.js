document.addEventListener("DOMContentLoaded", () => {
  const links = document.querySelectorAll("a[href]");

  links.forEach(link => {
    const url = link.getAttribute("href");

    // ignore logout & external links
    if (!url.startsWith("/") || url === "/logout") return;

    link.addEventListener("click", e => {
      e.preventDefault();
      const content = document.querySelector(".content");
      if (content) {
        content.classList.add("fade-out");
        setTimeout(() => {
          window.location.href = url;
        }, 200);
      } else {
        window.location.href = url;
      }
    });
  });
});
