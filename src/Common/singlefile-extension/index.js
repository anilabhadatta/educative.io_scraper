// working v1
/*
onload = async () => {
    const { content, title, filename } = await extension.getPageData({
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
        groupDuplicateImages: true
    });
    console.log(content);
    const base64 = btoa(unescape(encodeURIComponent(content)));

    // 3. Inject a script with the base64-encoded content
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.textContent = `
    window.getPageData = () => {
        const base64 = "${base64}";
        return decodeURIComponent(escape(atob(base64)));
    };
    `;
    
    // Wait for document.body or fallback to document.documentElement
    const targetElement = document.body ?? document.documentElement;
    
    // Append script directly — cloning is not necessary
    targetElement.appendChild(script);
    
}
*/

// working v2
/*
window.addEventListener("message", async (event) => {
    if (event.source !== window) return;
    if (event.data && event.data.type === "SF_SAVE_PAGE") {
        console.log("Page save triggered from console");

        const { content, title, filename } = await extension.getPageData({
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
            groupDuplicateImages: true
        });
            console.log("Done execution");
            console.log(content);
            const base64 = btoa(unescape(encodeURIComponent(content)));

            // 3. Inject a script with the base64-encoded content
            const script = document.createElement("script");
            script.type = "text/javascript";
            script.textContent = `
            window.getPageData = () => {
                const base64 = "${base64}";
                return decodeURIComponent(escape(atob(base64)));
            };
            `;
            
            // Wait for document.body or fallback to document.documentElement
            const targetElement = document.body ?? document.documentElement;
            
            // Append script directly — cloning is not necessary
            targetElement.appendChild(script);
    }
});


onload = async () => {
    console.log("injecting script")
        // 3. Inject a script with the base64-encoded content
    const script = document.createElement("script");
    script.className = "invisible-content";
    script.type = "text/javascript";
    script.textContent = `
    window.savePageTrigger = function () {
             window.postMessage({ type: "SF_SAVE_PAGE" }, "*");
        };
    `;
    
    // Wait for document.body or fallback to document.documentElement
    const targetElement = document.body ?? document.documentElement;
    
    // Append script directly — cloning is not necessary
    targetElement.appendChild(script);
    console.log("injecting done")
}
*/

//working v3
onload = async () => {
    console.log("Injecting script");
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.textContent = `
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
    `;
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
