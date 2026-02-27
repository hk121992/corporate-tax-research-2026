/**
 * presentation.js
 * 8-slide animated presentation overlay for the Corporate Tax Research webapp.
 * Self-contained vanilla JS — no imports required.
 * Exposes window.PresentationController with open() and close() methods.
 */

(function () {
  'use strict';

  // ─── Slide data ────────────────────────────────────────────────────────────

  var SLIDES = [
    {
      id: 'slide-title',
      theme: 'hero',
      title: 'Beyond Corporate Tax',
      subtitle: 'Total Economic Tax Contribution',
      body: null,
      bullets: null,
      stat: null,
      footer: 'Australia\'s 20 Largest Companies · FY2019-20 to FY2023-24'
    },
    {
      id: 'slide-problem',
      theme: 'dark',
      title: 'The Problem with Corporate Tax Headlines',
      subtitle: null,
      body: 'When media and policy debates focus exclusively on corporate income tax, they capture only a fraction of the economic contribution made by large companies.',
      bullets: [
        'Corporate tax is just one of many taxes large companies pay and collect.',
        'Total Tax Contribution (TTC) includes payroll tax, GST collected, customs duties, FBT, stamp duties and more.',
        'TTC is typically <strong>2× to 4×</strong> larger than corporate income tax alone.',
        'Ignoring TTC distorts public perception of corporate fiscal contribution.'
      ],
      stat: { value: '2–4×', label: 'TTC vs corporate tax alone' }
    },
    {
      id: 'slide-multiplier',
      theme: 'dark',
      title: 'The Employment Tax Multiplier',
      subtitle: null,
      body: 'The employment tax multiplier measures how much additional tax flows through wages and employment — on top of corporate income tax paid.',
      bullets: [
        '<strong>Retail sector</strong>: Woolworths 4.2×, Coles 4.1× — large workforces generate enormous payroll and income tax flows.',
        '<strong>Mining sector</strong>: BHP 1.2×, Rio Tinto 1.3× — capital-intensive operations mean fewer employees per dollar of revenue.',
        'A multiplier of 4× means that for every $1 of corporate tax, $4 flows through employment taxes.',
        'Policy that focuses only on corporate tax misses where the majority of economic contribution actually occurs.'
      ],
      stat: { value: '4.2×', label: 'Woolworths employment tax multiplier' }
    },
    {
      id: 'slide-ai-era',
      theme: 'dark',
      title: 'The AI-Era Signal',
      subtitle: null,
      body: 'Technology and AI-enabled companies generate exceptional revenue per employee — but this structural shift means less tax flows through employment.',
      bullets: [
        'High revenue-per-employee ratios (tech, platforms) produce concentrated corporate tax but minimal payroll tax.',
        'As AI scales revenue without scaling headcount, the gap between corporate tax and employment tax widens.',
        'Mining companies already demonstrate this pattern: high profits, low employment multipliers.',
        'Policymakers relying on employment taxes face a structural revenue challenge as AI penetrates every sector.'
      ],
      stat: { value: 'Revenue↑ Employees→', label: 'The AI-era fiscal gap' }
    },
    {
      id: 'slide-shareholders',
      theme: 'dark',
      title: 'Who Captures Profits? Tax vs Shareholders',
      subtitle: null,
      body: 'For many of Australia\'s largest companies, shareholders receive more in dividends and buybacks than the government collects in total tax contribution.',
      bullets: [
        'When shareholder returns exceed TTC, the distribution of economic surplus tilts decisively toward capital owners.',
        'Mining boom years (FY2020-21) saw particularly large shareholder distributions relative to TTC.',
        'Banks historically returned high dividends; COVID-19 forced dividend cuts, narrowing the gap temporarily.',
        'The parity line (dividends = TTC) is a powerful lens for evaluating who benefits most from company profits.'
      ],
      stat: { value: 'Dividends > TTC', label: 'For several top-20 companies' }
    },
    {
      id: 'slide-trend',
      theme: 'dark',
      title: 'Five-Year Trend: TTC Growth 2019–2024',
      subtitle: null,
      body: 'Total Tax Contribution from Australia\'s 20 largest companies grew substantially over the five-year period, driven by mining profits and economic recovery.',
      bullets: [
        '<strong>FY2019-20</strong>: $41.7B — COVID suppressed bank profits; mining was pre-boom.',
        '<strong>FY2020-21</strong>: Mining boom spike driven by iron ore price peak; BHP and Rio Tinto profits surged.',
        '<strong>FY2023-24</strong>: $69.8B — sustained growth; corporate tax share of TTC rising as employment taxes stabilise.',
        'The rising corporate tax share within TTC signals a structural shift in where economic contribution originates.'
      ],
      stat: { value: '$41.7B → $69.8B', label: 'TTC growth FY2019-20 to FY2023-24' }
    },
    {
      id: 'slide-covid',
      theme: 'dark',
      title: 'COVID\'s Tax Footprint',
      subtitle: null,
      body: 'The pandemic created extraordinary distortions in corporate tax: some of Australia\'s largest companies paid zero corporate income tax in FY2019-20.',
      bullets: [
        '<strong>Qantas</strong>: Zero corporate tax FY2019-20 due to pandemic losses, yet still contributed employment taxes as the workforce was maintained during the crisis.',
        '<strong>Westpac</strong>: AUSTRAC penalty and COVID provisions suppressed profits; $0 corporate tax despite being a Big 4 bank.',
        'Employment taxes continued to flow even when corporate tax fell to zero, demonstrating TTC\'s resilience as a measure.',
        'Post-COVID recovery saw corporate tax rebound sharply as provisions unwound and profits normalised.'
      ],
      stat: { value: '$0', label: 'Corporate tax: Qantas & Westpac FY2019-20' }
    },
    {
      id: 'slide-policy',
      theme: 'hero-end',
      title: 'Policy Implications',
      subtitle: null,
      body: null,
      bullets: [
        'Adopting TTC as the standard reporting framework gives a complete picture of corporate fiscal contribution.',
        'Employment tax multipliers should inform sector-specific policy, especially as AI reduces headcount across industries.',
        'As high-revenue, low-employment business models scale, reliance on employment taxes becomes structurally risky.',
        'Shareholder-vs-TTC analysis provides a distributional lens that corporate tax rates alone cannot offer.'
      ],
      stat: { value: 'Total Tax Contribution', label: 'The metric that matters' }
    }
  ];

  // ─── CSS injection ──────────────────────────────────────────────────────────

  function injectStyles() {
    if (document.getElementById('presentation-styles')) return;
    var style = document.createElement('style');
    style.id = 'presentation-styles';
    style.textContent = [
      '#presentation-overlay {',
      '  position: fixed;',
      '  inset: 0;',
      '  z-index: 9000;',
      '  background: #0b1120;',
      '  color: #e8edf5;',
      '  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;',
      '  display: flex;',
      '  flex-direction: column;',
      '  align-items: stretch;',
      '  overflow: hidden;',
      '  opacity: 0;',
      '  transition: opacity 0.3s ease;',
      '}',

      '#presentation-overlay.pres-visible {',
      '  opacity: 1;',
      '}',

      '#pres-topbar {',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: space-between;',
      '  padding: 14px 20px;',
      '  background: rgba(255,255,255,0.04);',
      '  border-bottom: 1px solid rgba(255,255,255,0.08);',
      '  flex-shrink: 0;',
      '}',

      '#pres-counter {',
      '  font-size: 13px;',
      '  color: rgba(255,255,255,0.5);',
      '  letter-spacing: 0.06em;',
      '  font-variant-numeric: tabular-nums;',
      '}',

      '#pres-close {',
      '  background: rgba(255,255,255,0.08);',
      '  border: 1px solid rgba(255,255,255,0.15);',
      '  color: #e8edf5;',
      '  border-radius: 6px;',
      '  padding: 6px 14px;',
      '  font-size: 13px;',
      '  cursor: pointer;',
      '  transition: background 0.2s;',
      '}',
      '#pres-close:hover { background: rgba(255,255,255,0.15); }',

      '#pres-stage {',
      '  flex: 1;',
      '  position: relative;',
      '  overflow: hidden;',
      '}',

      '.pres-slide {',
      '  position: absolute;',
      '  inset: 0;',
      '  display: flex;',
      '  flex-direction: column;',
      '  align-items: center;',
      '  justify-content: center;',
      '  padding: 40px 8vw;',
      '  box-sizing: border-box;',
      '  opacity: 0;',
      '  transform: translateX(60px);',
      '  transition: opacity 0.4s ease, transform 0.4s ease;',
      '  pointer-events: none;',
      '}',

      '.pres-slide.pres-active {',
      '  opacity: 1;',
      '  transform: translateX(0);',
      '  pointer-events: auto;',
      '}',

      '.pres-slide.pres-exit-left {',
      '  opacity: 0;',
      '  transform: translateX(-60px);',
      '}',

      '.pres-slide.pres-enter-right {',
      '  opacity: 0;',
      '  transform: translateX(60px);',
      '}',

      '.pres-slide.pres-enter-left {',
      '  opacity: 0;',
      '  transform: translateX(-60px);',
      '}',

      '.pres-slide.pres-exit-right {',
      '  opacity: 0;',
      '  transform: translateX(60px);',
      '}',

      /* Hero theme */
      '.pres-slide.theme-hero {',
      '  background: radial-gradient(ellipse at 30% 40%, #1a2f5e 0%, #0b1120 60%);',
      '}',

      '.pres-slide.theme-hero-end {',
      '  background: radial-gradient(ellipse at 70% 60%, #1a3a2e 0%, #0b1120 60%);',
      '}',

      '.pres-slide.theme-dark {',
      '  background: #0b1120;',
      '}',

      '.pres-slide-inner {',
      '  max-width: 820px;',
      '  width: 100%;',
      '}',

      '.pres-label {',
      '  font-size: 11px;',
      '  letter-spacing: 0.15em;',
      '  text-transform: uppercase;',
      '  color: #4a9eff;',
      '  margin-bottom: 16px;',
      '  font-weight: 600;',
      '}',

      '.pres-title {',
      '  font-size: clamp(26px, 4vw, 48px);',
      '  font-weight: 800;',
      '  line-height: 1.15;',
      '  margin: 0 0 10px;',
      '  color: #ffffff;',
      '}',

      '.pres-subtitle {',
      '  font-size: clamp(18px, 2.5vw, 28px);',
      '  font-weight: 300;',
      '  color: #7ab3ff;',
      '  margin: 0 0 24px;',
      '}',

      '.pres-body {',
      '  font-size: clamp(14px, 1.4vw, 17px);',
      '  line-height: 1.7;',
      '  color: rgba(255,255,255,0.75);',
      '  margin-bottom: 20px;',
      '}',

      '.pres-bullets {',
      '  list-style: none;',
      '  padding: 0;',
      '  margin: 0 0 24px;',
      '}',

      '.pres-bullets li {',
      '  font-size: clamp(13px, 1.3vw, 16px);',
      '  line-height: 1.65;',
      '  color: rgba(255,255,255,0.75);',
      '  padding: 6px 0 6px 22px;',
      '  position: relative;',
      '  border-bottom: 1px solid rgba(255,255,255,0.05);',
      '}',

      '.pres-bullets li:last-child { border-bottom: none; }',

      '.pres-bullets li::before {',
      '  content: "▸";',
      '  position: absolute;',
      '  left: 0;',
      '  color: #4a9eff;',
      '  font-size: 11px;',
      '  top: 9px;',
      '}',

      '.pres-stat {',
      '  display: inline-flex;',
      '  flex-direction: column;',
      '  align-items: flex-start;',
      '  background: rgba(74,158,255,0.1);',
      '  border: 1px solid rgba(74,158,255,0.3);',
      '  border-radius: 10px;',
      '  padding: 14px 22px;',
      '  margin-top: 8px;',
      '}',

      '.pres-stat-value {',
      '  font-size: clamp(22px, 3vw, 36px);',
      '  font-weight: 800;',
      '  color: #7ab3ff;',
      '  line-height: 1.1;',
      '}',

      '.pres-stat-label {',
      '  font-size: 12px;',
      '  color: rgba(255,255,255,0.5);',
      '  margin-top: 4px;',
      '  letter-spacing: 0.04em;',
      '}',

      '.pres-footer-text {',
      '  font-size: 12px;',
      '  color: rgba(255,255,255,0.3);',
      '  margin-top: 20px;',
      '  letter-spacing: 0.05em;',
      '}',

      '#pres-bottombar {',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: space-between;',
      '  padding: 14px 20px;',
      '  background: rgba(255,255,255,0.04);',
      '  border-top: 1px solid rgba(255,255,255,0.08);',
      '  flex-shrink: 0;',
      '}',

      '.pres-nav-btn {',
      '  background: rgba(74,158,255,0.15);',
      '  border: 1px solid rgba(74,158,255,0.3);',
      '  color: #7ab3ff;',
      '  border-radius: 8px;',
      '  padding: 9px 22px;',
      '  font-size: 14px;',
      '  font-weight: 600;',
      '  cursor: pointer;',
      '  transition: background 0.2s, transform 0.1s;',
      '  min-width: 90px;',
      '}',

      '.pres-nav-btn:hover { background: rgba(74,158,255,0.28); }',
      '.pres-nav-btn:active { transform: scale(0.96); }',
      '.pres-nav-btn:disabled { opacity: 0.3; cursor: default; }',

      '#pres-dots {',
      '  display: flex;',
      '  gap: 8px;',
      '  align-items: center;',
      '}',

      '.pres-dot {',
      '  width: 8px;',
      '  height: 8px;',
      '  border-radius: 50%;',
      '  background: rgba(255,255,255,0.2);',
      '  cursor: pointer;',
      '  transition: background 0.2s, transform 0.2s;',
      '}',

      '.pres-dot.pres-dot-active {',
      '  background: #4a9eff;',
      '  transform: scale(1.3);',
      '}',

      /* Mobile adjustments */
      '@media (max-width: 600px) {',
      '  .pres-slide { padding: 24px 5vw; }',
      '  .pres-nav-btn { padding: 9px 14px; min-width: 70px; font-size: 13px; }',
      '  #pres-topbar, #pres-bottombar { padding: 10px 14px; }',
      '}'
    ].join('\n');
    document.head.appendChild(style);
  }

  // ─── Build DOM ─────────────────────────────────────────────────────────────

  function buildSlideHTML(slide, index) {
    var themeClass = 'theme-' + slide.theme;
    var inner = '<div class="pres-slide-inner">';

    if (index === 0) {
      // Hero slide
      inner += '<div class="pres-label">Research Presentation</div>';
      inner += '<h2 class="pres-title">' + escapeHTML(slide.title) + '</h2>';
      if (slide.subtitle) {
        inner += '<p class="pres-subtitle">' + escapeHTML(slide.subtitle) + '</p>';
      }
      if (slide.footer) {
        inner += '<p class="pres-footer-text">' + escapeHTML(slide.footer) + '</p>';
      }
    } else {
      inner += '<h2 class="pres-title">' + escapeHTML(slide.title) + '</h2>';
      if (slide.body) {
        inner += '<p class="pres-body">' + escapeHTML(slide.body) + '</p>';
      }
      if (slide.bullets && slide.bullets.length) {
        inner += '<ul class="pres-bullets">';
        slide.bullets.forEach(function (b) {
          inner += '<li>' + b + '</li>'; // allow inline HTML in bullets
        });
        inner += '</ul>';
      }
      if (slide.stat) {
        inner += '<div class="pres-stat">';
        inner += '<span class="pres-stat-value">' + escapeHTML(slide.stat.value) + '</span>';
        inner += '<span class="pres-stat-label">' + escapeHTML(slide.stat.label) + '</span>';
        inner += '</div>';
      }
    }

    inner += '</div>';

    return inner;
  }

  function escapeHTML(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildOverlay() {
    if (document.getElementById('presentation-overlay')) return;

    injectStyles();

    var overlay = document.createElement('div');
    overlay.id = 'presentation-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Presentation overlay');
    overlay.style.display = 'none';

    // Top bar
    var topbar = document.createElement('div');
    topbar.id = 'pres-topbar';
    topbar.innerHTML = [
      '<span id="pres-counter">1 / ' + SLIDES.length + '</span>',
      '<button id="pres-close" aria-label="Close presentation">✕ Close</button>'
    ].join('');
    overlay.appendChild(topbar);

    // Stage
    var stage = document.createElement('div');
    stage.id = 'pres-stage';

    SLIDES.forEach(function (slide, i) {
      var el = document.createElement('div');
      el.className = 'pres-slide theme-' + slide.theme + (i === 0 ? ' pres-active' : '');
      el.id = slide.id;
      el.setAttribute('aria-hidden', i === 0 ? 'false' : 'true');
      el.innerHTML = buildSlideHTML(slide, i);
      stage.appendChild(el);
    });

    overlay.appendChild(stage);

    // Bottom bar
    var bottombar = document.createElement('div');
    bottombar.id = 'pres-bottombar';

    var btnPrev = document.createElement('button');
    btnPrev.id = 'pres-btn-prev';
    btnPrev.className = 'pres-nav-btn';
    btnPrev.textContent = '← Prev';
    btnPrev.disabled = true;

    var dots = document.createElement('div');
    dots.id = 'pres-dots';
    SLIDES.forEach(function (_, i) {
      var dot = document.createElement('button');
      dot.className = 'pres-dot' + (i === 0 ? ' pres-dot-active' : '');
      dot.setAttribute('aria-label', 'Go to slide ' + (i + 1));
      dot.dataset.slide = i;
      dots.appendChild(dot);
    });

    var btnNext = document.createElement('button');
    btnNext.id = 'pres-btn-next';
    btnNext.className = 'pres-nav-btn';
    btnNext.textContent = 'Next →';

    bottombar.appendChild(btnPrev);
    bottombar.appendChild(dots);
    bottombar.appendChild(btnNext);
    overlay.appendChild(bottombar);

    document.body.appendChild(overlay);
  }

  // ─── Controller ────────────────────────────────────────────────────────────

  var currentSlide = 0;
  var isAnimating = false;
  var touchStartX = 0;
  var touchStartY = 0;

  function getSlideEls() {
    return document.querySelectorAll('.pres-slide');
  }

  function getDotEls() {
    return document.querySelectorAll('.pres-dot');
  }

  function updateCounter() {
    var counter = document.getElementById('pres-counter');
    if (counter) counter.textContent = (currentSlide + 1) + ' / ' + SLIDES.length;
  }

  function updateDots() {
    getDotEls().forEach(function (dot, i) {
      dot.classList.toggle('pres-dot-active', i === currentSlide);
    });
  }

  function updateNavButtons() {
    var prev = document.getElementById('pres-btn-prev');
    var next = document.getElementById('pres-btn-next');
    if (prev) prev.disabled = currentSlide === 0;
    if (next) {
      if (currentSlide === SLIDES.length - 1) {
        next.textContent = 'Finish';
      } else {
        next.textContent = 'Next →';
      }
    }
  }

  function goToSlide(index, direction) {
    if (isAnimating) return;
    if (index < 0 || index >= SLIDES.length) return;
    if (index === currentSlide) return;

    isAnimating = true;
    var slides = getSlideEls();
    var oldSlide = slides[currentSlide];
    var newSlide = slides[index];

    // direction: 'next' means new slide comes from right, 'prev' from left
    var enterClass = direction === 'prev' ? 'pres-enter-left' : 'pres-enter-right';
    var exitClass = direction === 'prev' ? 'pres-exit-right' : 'pres-exit-left';

    // Prepare new slide off-screen
    newSlide.classList.add(enterClass);
    newSlide.style.display = '';
    newSlide.setAttribute('aria-hidden', 'false');

    // Trigger layout
    void newSlide.offsetWidth;

    // Animate out old, animate in new
    oldSlide.classList.add(exitClass);
    oldSlide.classList.remove('pres-active');
    newSlide.classList.remove(enterClass);
    newSlide.classList.add('pres-active');

    var prev2 = currentSlide;
    currentSlide = index;
    updateCounter();
    updateDots();
    updateNavButtons();

    setTimeout(function () {
      slides[prev2].classList.remove(exitClass);
      slides[prev2].setAttribute('aria-hidden', 'true');
      isAnimating = false;
    }, 420);
  }

  function nextSlide() {
    if (currentSlide === SLIDES.length - 1) {
      PresentationController.close();
    } else {
      goToSlide(currentSlide + 1, 'next');
    }
  }

  function prevSlide() {
    goToSlide(currentSlide - 1, 'prev');
  }

  function handleKeydown(e) {
    switch (e.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        e.preventDefault();
        nextSlide();
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault();
        prevSlide();
        break;
      case 'Escape':
        PresentationController.close();
        break;
      default:
        break;
    }
  }

  function handleTouchStart(e) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }

  function handleTouchEnd(e) {
    var dx = e.changedTouches[0].clientX - touchStartX;
    var dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 40) {
      if (dx < 0) {
        nextSlide();
      } else {
        prevSlide();
      }
    }
  }

  function attachEvents() {
    var overlay = document.getElementById('presentation-overlay');
    var closeBtn = document.getElementById('pres-close');
    var nextBtn = document.getElementById('pres-btn-next');
    var prevBtn = document.getElementById('pres-btn-prev');

    closeBtn.addEventListener('click', function () { PresentationController.close(); });
    nextBtn.addEventListener('click', nextSlide);
    prevBtn.addEventListener('click', prevSlide);

    getDotEls().forEach(function (dot) {
      dot.addEventListener('click', function () {
        var idx = parseInt(dot.dataset.slide, 10);
        var dir = idx > currentSlide ? 'next' : 'prev';
        goToSlide(idx, dir);
      });
    });

    document.addEventListener('keydown', handleKeydown);

    overlay.addEventListener('touchstart', handleTouchStart, { passive: true });
    overlay.addEventListener('touchend', handleTouchEnd, { passive: true });
  }

  // ─── Public API ─────────────────────────────────────────────────────────────

  var PresentationController = {
    open: function () {
      buildOverlay();

      // Reset to slide 0
      currentSlide = 0;
      isAnimating = false;
      var slides = getSlideEls();
      slides.forEach(function (s, i) {
        s.classList.remove('pres-active', 'pres-exit-left', 'pres-exit-right', 'pres-enter-left', 'pres-enter-right');
        s.setAttribute('aria-hidden', i === 0 ? 'false' : 'true');
        if (i === 0) s.classList.add('pres-active');
      });
      updateCounter();
      updateDots();
      updateNavButtons();

      // Re-attach events each open (safe with removeEventListener pattern omitted for simplicity;
      // events are attached only once via the _eventsAttached guard)
      if (!PresentationController._eventsAttached) {
        attachEvents();
        PresentationController._eventsAttached = true;
      }

      var overlay = document.getElementById('presentation-overlay');
      overlay.style.display = 'flex';
      document.body.style.overflow = 'hidden';

      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          overlay.classList.add('pres-visible');
        });
      });

      // Focus the overlay for keyboard accessibility
      overlay.focus && overlay.setAttribute('tabindex', '-1');
      setTimeout(function () { overlay.focus(); }, 50);
    },

    close: function () {
      var overlay = document.getElementById('presentation-overlay');
      if (!overlay) return;
      overlay.classList.remove('pres-visible');
      document.removeEventListener('keydown', handleKeydown);
      PresentationController._eventsAttached = false;
      document.body.style.overflow = '';
      setTimeout(function () {
        overlay.style.display = 'none';
      }, 320);
    },

    _eventsAttached: false
  };

  window.PresentationController = PresentationController;

  // ─── Auto-wire "▶ Present" button if present ────────────────────────────────

  function wireButton() {
    var btn = document.getElementById('btn-present');
    if (btn) {
      btn.addEventListener('click', function () {
        PresentationController.open();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireButton);
  } else {
    wireButton();
  }

}());
