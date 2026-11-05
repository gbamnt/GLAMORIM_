/** Build local (sem CDN): npx tailwindcss@3.4.17 -i ui/input.css -o ui/styles.css --minify */
module.exports = {
  content: ['./ui/index.html', './ui/app.js'],
  theme: { extend: {} },
  plugins: [],
};
