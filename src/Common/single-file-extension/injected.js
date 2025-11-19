window.savePageTrigger = function () {
    return new Promise(resolve => {
        const handler = (event) => {
            if (event.source === window && event.data.type === "SF_PAGE_DATA") {
                window.removeEventListener("message", handler);
                resolve(event.data.content);
            }
        };
        window.addEventListener("message", handler);
        window.postMessage({ type: "SF_SAVE_PAGE" }, "*");
    });
};