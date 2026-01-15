const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false }); // Show browser for debugging
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('Navigating to login page...');
    await page.goto('http://localhost:3002/auth/login');
    await page.waitForLoadState('networkidle');

    // Take screenshot of login page first
    await page.screenshot({ path: '/tmp/send-buddy-login.png', fullPage: true });
    console.log('Login page captured');

    // Fill in login form
    console.log('Logging in...');
    await page.fill('input[type="email"]', 'test@test.com');
    await page.fill('input[type="password"]', 'TestPass123');

    // Click login and wait a bit
    await page.click('button[type="submit"]');
    console.log('Clicked submit button');

    // Wait and see what happens
    await page.waitForTimeout(5000);
    console.log('Current URL after login attempt:', page.url());

    // Take screenshot after login attempt
    await page.screenshot({ path: '/tmp/send-buddy-after-login.png', fullPage: true });

    // Try to navigate to trips
    await page.goto('http://localhost:3002/trips');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    console.log('Current URL after going to trips:', page.url());

    // Desktop screenshots (1280px)
    await page.setViewportSize({ width: 1280, height: 800 });

    // 1. Trips page
    console.log('Capturing /trips page...');
    await page.screenshot({ path: '/tmp/send-buddy-trips-desktop.png', fullPage: true });

    // 2. Create trip page
    console.log('Capturing /trips/new page...');
    await page.goto('http://localhost:3002/trips/new');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-trips-new-desktop.png', fullPage: true });

    // 3. Matches page
    console.log('Capturing /matches page...');
    await page.goto('http://localhost:3002/matches');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-matches-desktop.png', fullPage: true });

    // 4. Sessions page
    console.log('Capturing /sessions page...');
    await page.goto('http://localhost:3002/sessions');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-sessions-desktop.png', fullPage: true });

    // 5. Profile page
    console.log('Capturing /profile page...');
    await page.goto('http://localhost:3002/profile');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-profile-desktop.png', fullPage: true });

    // Mobile screenshots (375px)
    await page.setViewportSize({ width: 375, height: 667 });

    console.log('Capturing mobile versions...');

    await page.goto('http://localhost:3002/trips');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-trips-mobile.png', fullPage: true });

    await page.goto('http://localhost:3002/trips/new');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-trips-new-mobile.png', fullPage: true });

    await page.goto('http://localhost:3002/matches');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-matches-mobile.png', fullPage: true });

    await page.goto('http://localhost:3002/sessions');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-sessions-mobile.png', fullPage: true });

    await page.goto('http://localhost:3002/profile');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/send-buddy-profile-mobile.png', fullPage: true });

    console.log('All screenshots captured successfully!');

    await page.waitForTimeout(3000); // Keep browser open for a moment
  } catch (error) {
    console.error('Error:', error.message);
    console.error('Stack:', error.stack);
    await page.screenshot({ path: '/tmp/send-buddy-error.png' });
    await page.waitForTimeout(3000);
  } finally {
    await browser.close();
  }
})();
