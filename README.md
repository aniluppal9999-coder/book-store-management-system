# BookStore Management System — GitHub Pages edition

A responsive bookstore management demo built with HTML, CSS and JavaScript. It is designed to run directly on GitHub Pages, without Flask or a server-side database, so it avoids the HTTP 500 error caused by trying to run a Python backend on GitHub Pages.

## Features
- Dashboard with catalogue, stock, sales and low-stock summaries
- Add, edit, search and delete book records
- Inventory quantity updates and low-stock indicators
- Billing cart with stock validation, discount, tax and receipt
- Sales history and CSV export
- Browser localStorage persistence
- Responsive layout for desktop and mobile

## Publish on GitHub Pages
1. Upload `index.html`, `style.css`, `app.js`, and `README.md` to the root of your GitHub repository.
2. Open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select branch `main` and folder `/ (root)`, then click **Save**.
5. Wait for GitHub Pages to publish, then open the URL shown on the Pages settings screen.

## Important data note
This edition stores data in the current browser using `localStorage`. It is suitable for a student project demo, but it is not a shared multi-user database. Data is not synced between devices or browsers. Export sales to CSV regularly. Do not use this demo for real customer or payment data.

## Included sample data
The first run includes a few example books so the dashboard is not empty. You can edit or delete these and add your own. Use the browser's developer tools to clear local storage if you want to reset the demo.
