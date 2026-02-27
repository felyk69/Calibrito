const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    const errors = [];
    page.on('pageerror', error => {
        errors.push(error.message);
    });
    page.on('console', msg => {
        console.log(`BROWSER LOG [${msg.type()}]: ${msg.text()}`);
    });

    try {
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' });
        console.log("Page loaded");

        // Wait for first 50 books to load
        await page.waitForTimeout(2000);

        // Scroll down
        console.log("Scrolling down to trigger IntersectionObserver...");
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        console.log("Errors captured:");
        console.log(JSON.stringify(errors, null, 2));

    } catch (e) {
        console.error("Test script failed:", e);
    } finally {
        await browser.close();
    }
})();
