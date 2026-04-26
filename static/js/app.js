document.querySelectorAll("[data-confirm]").forEach((element) => {
    element.addEventListener("click", (event) => {
        const message = element.getAttribute("data-confirm") || "Are you sure?";
        if (!window.confirm(message)) {
            event.preventDefault();
        }
    });
});

setTimeout(() => {
    document.querySelectorAll(".flash").forEach((flash) => {
        flash.style.opacity = "0";
        flash.style.transform = "translateY(-4px)";
        flash.style.transition = "all 0.35s ease";
        setTimeout(() => flash.remove(), 350);
    });
}, 3500);
