onload = async () => {
    console.log("Injecting script");
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = chrome.runtime.getURL("injected.js");
    (document.body ?? document.documentElement).appendChild(script);
    console.log("Injecting done");
};


window.addEventListener("message", async (event) => {
    if (event.source !== window) return;
    if (event.data?.type === "SF_SAVE_PAGE") {
        console.log("Page save triggered from console");

        const { content } = await extension.getPageData({
            removeHiddenElements: true,
            removeUnusedStyles: true,
            removeUnusedFonts: true,
            removeImports: true,
            removeScripts: true,
            compressHTML: true,
            removeAudioSrc: true,
            removeVideoSrc: true,
            removeAlternativeFonts: true,
            removeAlternativeMedias: true,
            removeAlternativeImages: true,
            groupDuplicateImages: true,
            blockVideos: true,
            blockScripts: true,
            networkTimeout: 60000
        });
        console.log("getPageData execution complete")
        window.postMessage({ type: "SF_PAGE_DATA", content }, "*");
    }
});