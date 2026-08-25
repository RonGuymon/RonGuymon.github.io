// Mobile nav toggle
const navToggle = document.querySelector(".nav-toggle");
const siteNav = document.querySelector(".site-nav");
if (navToggle && siteNav) {
  navToggle.addEventListener("click", () => {
    const isOpen = siteNav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
  siteNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => siteNav.classList.remove("open"));
  });
}

// Headshot: fall back to the initials placeholder if no real photo exists yet
const headshot = document.getElementById("headshot");
if (headshot) {
  headshot.addEventListener("error", () => {
    headshot.src = "assets/img/headshot-placeholder.svg";
  }, { once: true });
}

// Lightbox for the photo mosaic
const lightbox = document.querySelector(".lightbox");
const lightboxImg = lightbox ? lightbox.querySelector("img") : null;
document.querySelectorAll("[data-lightbox]").forEach((trigger) => {
  trigger.addEventListener("click", () => {
    lightboxImg.src = trigger.dataset.lightbox;
    lightbox.classList.add("open");
  });
});
if (lightbox) {
  lightbox.addEventListener("click", () => lightbox.classList.remove("open"));
}

// Autoplay the tool-journey video once it scrolls into view (saves bandwidth on load)
const lazyVideo = document.querySelector("video[data-autoplay]");
if (lazyVideo) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        lazyVideo.play().catch(() => {});
      }
    });
  }, { threshold: 0.35 });
  observer.observe(lazyVideo);
}
