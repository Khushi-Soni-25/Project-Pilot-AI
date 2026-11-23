/* ==========================================================================
   Icon sprite. Injected inline so icons work on any host, including file://.
   Usage: <svg class="icon" aria-hidden="true"><use href="#i-search"></use></svg>
   or in JS: icon("search")
   ========================================================================== */

(() => {
  const paths = {
    logo: '<path d="M12 3l2.4 6.1L21 12l-6.6 2.9L12 21l-2.4-6.1L3 12l6.6-2.9z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    route: '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H15a3.5 3.5 0 000-7H9a3.5 3.5 0 010-7h6.5"/>',
    layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    code: '<path d="M8 8l-5 4 5 4M16 8l5 4-5 4M14 5l-4 14"/>',
    database: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.7 4 5.7 4 9s-1.4 6.3-4 9c-2.6-2.7-4-5.7-4-9s1.4-6.3 4-9z"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    github: '<path d="M9 19c-4 1.3-4-2-6-2.5m12 5v-3.5c0-1 .1-1.4-.5-2 2.800-.3 5.500-1.400 5.500-6a4.600 4.600 0 00-1.300-3.200 4.300 4.300 0 00-.1-3.200s-1-.3-3.500 1.300a12 12 0 00-6.200 0C6.400 2.800 5.400 3.100 5.400 3.100a4.300 4.300 0 00-.1 3.200A4.600 4.600 0 004 9.500c0 4.600 2.700 5.700 5.500 6-.6.600-.6 1.200-.5 2V21"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.500" y="9.500" width="5" height="5" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    book: '<path d="M4 5.500A2.500 2.500 0 016.500 3H20v16H6.500A2.500 2.500 0 004 21.500z"/><path d="M4 21.500V5.500M8 7h8"/>',
    link: '<path d="M10 14a4.500 4.500 0 006.400 0l3-3a4.500 4.500 0 00-6.400-6.400l-1 1M14 10a4.500 4.500 0 00-6.400 0l-3 3a4.500 4.500 0 006.400 6.400l1-1"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>',
    rocket: '<path d="M5 15c-1.500 1.300-2 5-2 5s3.700-.5 5-2c.700-.8.700-2.100-.1-2.900S5.800 14.300 5 15z"/><path d="M12 15l-3-3a22 22 0 012-4 12.800 12.800 0 018-5c.3 2.700-.2 7.500-5 10a22 22 0 01-4 2z"/><path d="M9 12H4s.5-3 2-4c1.600-1.100 5 0 5 0M12 15v5s3-.5 4-2c1.100-1.600 0-5 0-5"/>',
    zap: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    refresh: '<path d="M20 11a8 8 0 00-14.500-4M4 5v4h4M4 13a8 8 0 0014.500 4M20 19v-4h-4"/>',
    terminal: '<path d="M4 17l6-5-6-5M12 19h8"/>',
    compass: '<circle cx="12" cy="12" r="9"/><path d="M15.500 8.500l-2 5-5 2 2-5z"/>',
    chevron: '<path d="M6 9l6 6 6-6"/>',
    inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.500 5.100L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.500-6.900A2 2 0 0016.800 4H7.200a2 2 0 00-1.700 1.100z"/>',
    alert: '<path d="M10.300 3.900L1.800 18a2 2 0 001.700 3h17a2 2 0 001.700-3L13.700 3.900a2 2 0 00-3.400 0zM12 9v4M12 17h0"/>',
    flag: '<path d="M4 22V4M4 4h13l-2 4 2 4H4"/>',
    wrench: '<path d="M14.700 6.300a4 4 0 005 5L21 13l-8 8a2.800 2.800 0 01-4-4l8-8z" transform="scale(.9) translate(1.300 .5)"/><path d="M7 7l3 3"/>',
  };

  const sprite =
    '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">' +
    Object.entries(paths)
      .map(([name, d]) => `<symbol id="i-${name}" viewBox="0 0 24 24">${d}</symbol>`)
      .join("") +
    "</svg>";

  const mount = () => document.body.insertAdjacentHTML("afterbegin", sprite);
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);

  /** Returns an <svg> icon string for use in JS templates. */
  window.icon = (name, cls = "") =>
    `<svg class="icon ${cls}" aria-hidden="true" focusable="false"><use href="#i-${name}"></use></svg>`;
})();
