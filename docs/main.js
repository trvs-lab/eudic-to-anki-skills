const nav = document.querySelector(".site-nav");
const revealTargets = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.18, rootMargin: "0px 0px -12% 0px" }
);

revealTargets.forEach((item) => observer.observe(item));

window.addEventListener(
  "scroll",
  () => {
    if (!nav) {
      return;
    }
    nav.classList.toggle("is-scrolled", window.scrollY > 10);
  },
  { passive: true }
);
