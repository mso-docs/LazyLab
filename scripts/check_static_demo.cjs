/** Browser checks for the buildless Pages demo. Optional Playwright dependency. */
const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch();try {const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true});
 const page=await context.newPage();const errors=[];const external=[];
 page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!request.url().startsWith('http://127.0.0.1:8080'))external.push(request.url());});
 await context.route('https://www.youtube-nocookie.com/**',route=>route.fulfill({contentType:'text/html',body:'<html><title>Video embed test boundary</title></html>'}));
 await page.goto('http://127.0.0.1:8080');await page.getByRole('status').filter({hasText:'5 original measurements'}).waitFor();
 assert.equal(await page.locator('.bar-row').count(),5);
 await page.getByLabel('Measurement phase').selectOption('confirmatory');assert.equal(await page.locator('.bar-row').count(),3);
 await page.getByRole('tab',{name:'Experiment table',exact:true}).click();assert.equal(await page.locator('#rows tr').count(),3);
 await page.getByRole('tab',{name:'Experiment table',exact:true}).press('ArrowRight');assert.equal(await page.getByRole('tab',{name:'What this means'}).getAttribute('aria-selected'),'true');
 await page.getByRole('button',{name:'Switch to dark theme'}).click();await page.reload();assert.equal(await page.locator('body').getAttribute('class'),'dark');
 await page.getByRole('button',{name:'Switch to light theme'}).click();
 await page.getByLabel('Testable question').fill('Does correction improve held-out Brier score?');await page.getByLabel('Competing explanation').fill('Calibration error may offset correction.');
 await page.getByLabel('Maximum experiments').fill('4');await page.getByLabel('Reserved confirmation seeds').fill('4');await page.getByRole('button',{name:'Download design notes'}).click();await page.getByRole('status').filter({hasText:'Leave room for exploration'}).waitFor();
 await page.getByLabel('Maximum experiments').fill('6');
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download design notes'}).click()]);
 const data=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.equal(data.maximum_experiments,6);assert.match(data.kind,/not executable/);
 await page.getByRole('tab',{name:'Measurements',exact:true}).click();await page.getByLabel('Measurement phase').selectOption('all');await page.locator('header').scrollIntoViewIfNeeded();
 await page.screenshot({path:'/tmp/lazylab-pages-desktop.png',fullPage:true});
 assert.equal(external.length,0,'No external requests before explicit video playback');
 await page.goto('http://127.0.0.1:8080/help.html');assert.equal(await page.locator('iframe').count(),0);
 await page.getByRole('button',{name:'Load YouTube walkthrough'}).click();await page.locator('iframe').waitFor();assert.match(await page.locator('iframe').getAttribute('src'),/youtube-nocookie.com\/embed\/UV3h4IRk3go/);
 await page.getByRole('button',{name:'1:01 Guest restore'}).click();assert.match(await page.locator('iframe').getAttribute('src'),/start=61/);
 await page.getByText('What does this website store or send?',{exact:true}).click();assert.equal(await page.locator('#privacy').getAttribute('open'),'');
 await page.screenshot({path:'/tmp/lazylab-pages-help.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:8080');await page.getByRole('status').filter({hasText:'5 original measurements'}).waitFor();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'Mobile page must not overflow horizontally');
 await page.screenshot({path:'/tmp/lazylab-pages-mobile.png',fullPage:true});
 await page.goto('http://127.0.0.1:8080/help.html');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);await browser.close();console.log('Static demo checks passed: real data/filtering, keyboard tabs, persistent theme, planning validation/download, video consent/chapters, privacy disclosure, mobile layout; no JS errors. YouTube network mocked after explicit playback; streaming not tested.');
} finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
