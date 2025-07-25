// cand.js
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setUserAgent(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'
  );
  // Referer 헤더가 필요하면 page.setExtraHTTPHeaders로 추가 가능
  await page.goto('https://candfans.jp/api/contents/get-timeline/968402', {
    waitUntil: 'networkidle2',
  });
  const content = await page.evaluate(() => document.querySelector("body").innerText);
  console.log(JSON.parse(content));
  await browser.close();
})();
