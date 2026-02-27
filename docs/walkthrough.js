/**
 * walkthrough.js
 * 5-step interactive guided tour using tooltip-style overlays anchored to
 * real page elements in the Corporate Tax Research webapp.
 * Self-contained vanilla JS — no imports required.
 * Exposes window.WalkthroughController with start() and stop() methods.
 */

(function () {
  'use strict';

  // ─── Step definitions ───────────────────────────────────────────────────────

  var STEPS = [
    {
      target: '#chart-bar',
      title: 'Stacked Bars: Total Tax Contribution',
      body: 'Each stacked bar shows the full Total Tax Contribution (TTC) for one company, broken into components: corporate income tax (blue), payroll and employment taxes (green), GST collected, customs duties, and other taxes. Toggle individual tax components using the legend checkboxes above the chart to compare how each category contributes to a company\'s total fiscal footprint.',
      position: 'bottom'
    },
    {
      target: '.year-selector',
      title: 'Switch Financial Years',
      body: 'Use these buttons to jump between FY2019-20 and FY2023-24. Every chart updates simultaneously when you switch years. Compare FY2019-20 (COVID-depressed profits, especially banks) with FY2020-21 (the iron ore boom that supercharged mining TTC) and FY2023-24 (the most recent year, showing the highest aggregate TTC at $69.8B).',
      position: 'bottom'
    },
    {
      target: '#chart-scatter',
      title: 'Employment Tax Multiplier Bubble Chart',
      body: 'The horizontal axis shows corporate income tax; the vertical axis shows employment-related taxes. The ratio between them is the Employment Tax Multiplier. Retail companies (Woolworths 4.2×, Coles 4.1×) sit high on the vertical axis because their large workforces generate enormous payroll and income tax flows. Mining companies (BHP 1.2×) sit low — they are capital-intensive and generate less tax through employment. As AI scales revenue per employee, this gap matters enormously for future government revenues.',
      position: 'top'
    },
    {
      target: '#chart-tsr',
      title: 'Who Captures Profits?',
      body: 'This scatter plot compares Total Tax Contribution (x-axis) against total shareholder returns — dividends plus buybacks (y-axis). The diagonal parity line marks where shareholder returns equal TTC. Points above the line mean shareholders received more than the government collected in total taxes. Mining boom years produced several notable outliers above the parity line, raising questions about the distribution of economic surplus from Australia\'s largest companies.',
      position: 'top'
    },
    {
      target: '#chart-trend',
      title: 'Five-Year Trend',
      body: 'This line chart plots aggregate TTC from FY2019-20 ($41.7B) through FY2023-24 ($69.8B) for all 20 companies combined. Watch for the FY2020-21 spike driven by the iron ore price peak, and the gradual rise in corporate tax\'s share of TTC over the period — a structural signal that employment-linked taxes are growing more slowly than profits, consistent with the AI-era dynamic playing out across sectors.',
      position: 'top'
    }
  ];

  // ─── CSS injection ──────────────────────────────────────────────────────────

  function injectStyles() {
    if (document.getElementById('walkthrough-styles')) return;
    var style = document.createElement('style');
    style.id = 'walkthrough-styles';
    style.textContent = [
      /* Backdrop */
      '#walkthrough-overlay {',
      '  position: fixed;',
      '  inset: 0;',
      '  z-index: 8000;',
      '  pointer-events: none;',
      '}',

      '#walkthrough-overlay.wt-active {',
      '  pointer-events: auto;',
      '}',

      /* Dark scrim with a hole punched out via box-shadow */
      '#wt-scrim {',
      '  position: fixed;',
      '  inset: 0;',
      '  background: rgba(10, 16, 30, 0.72);',
      '  z-index: 8001;',
      '  transition: opacity 0.3s ease;',
      '  opacity: 0;',
      '  pointer-events: none;',
      '}',

      '#wt-scrim.wt-scrim-visible {',
      '  opacity: 1;',
      '  pointer-events: auto;',
      '}',

      /* Highlight pulse ring around the target */
      '#wt-highlight {',
      '  position: fixed;',
      '  z-index: 8002;',
      '  border-radius: 8px;',
      '  pointer-events: none;',
      '  transition: top 0.35s ease, left 0.35s ease, width 0.35s ease, height 0.35s ease, opacity 0.3s ease;',
      '  opacity: 0;',
      '}',

      '#wt-highlight.wt-highlight-visible {',
      '  opacity: 1;',
      '}',

      '#wt-highlight::before {',
      '  content: "";',
      '  position: absolute;',
      '  inset: -4px;',
      '  border-radius: 10px;',
      '  border: 2px solid rgba(74, 158, 255, 0.9);',
      '  animation: wt-pulse 1.8s ease-in-out infinite;',
      '}',

      '#wt-highlight::after {',
      '  content: "";',
      '  position: absolute;',
      '  inset: -10px;',
      '  border-radius: 14px;',
      '  border: 1px solid rgba(74, 158, 255, 0.35);',
      '  animation: wt-pulse 1.8s ease-in-out infinite 0.3s;',
      '}',

      '@keyframes wt-pulse {',
      '  0%, 100% { opacity: 0.8; transform: scale(1); }',
      '  50% { opacity: 0.3; transform: scale(1.015); }',
      '}',

      /* Tooltip card */
      '#wt-tooltip {',
      '  position: fixed;',
      '  z-index: 8010;',
      '  width: min(420px, 92vw);',
      '  background: #131c2e;',
      '  border: 1px solid rgba(74,158,255,0.35);',
      '  border-radius: 12px;',
      '  padding: 22px 24px 18px;',
      '  box-shadow: 0 8px 40px rgba(0,0,0,0.55), 0 0 0 1px rgba(74,158,255,0.08);',
      '  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;',
      '  color: #e8edf5;',
      '  opacity: 0;',
      '  transform: translateY(10px);',
      '  transition: opacity 0.3s ease, transform 0.3s ease;',
      '  box-sizing: border-box;',
      '}',

      '#wt-tooltip.wt-tooltip-visible {',
      '  opacity: 1;',
      '  transform: translateY(0);',
      '}',

      '#wt-tooltip-arrow {',
      '  position: absolute;',
      '  width: 12px;',
      '  height: 12px;',
      '  background: #131c2e;',
      '  border-top: 1px solid rgba(74,158,255,0.35);',
      '  border-left: 1px solid rgba(74,158,255,0.35);',
      '  transform: rotate(45deg);',
      '}',

      '#wt-step-counter {',
      '  font-size: 11px;',
      '  letter-spacing: 0.12em;',
      '  text-transform: uppercase;',
      '  color: #4a9eff;',
      '  font-weight: 700;',
      '  margin-bottom: 10px;',
      '}',

      '#wt-tooltip-title {',
      '  font-size: 16px;',
      '  font-weight: 700;',
      '  color: #ffffff;',
      '  margin: 0 0 10px;',
      '  line-height: 1.3;',
      '}',

      '#wt-tooltip-body {',
      '  font-size: 13.5px;',
      '  line-height: 1.65;',
      '  color: rgba(255,255,255,0.72);',
      '  margin: 0 0 18px;',
      '}',

      '#wt-tooltip-buttons {',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: space-between;',
      '  gap: 10px;',
      '}',

      '.wt-btn {',
      '  background: rgba(74,158,255,0.15);',
      '  border: 1px solid rgba(74,158,255,0.3);',
      '  color: #7ab3ff;',
      '  border-radius: 7px;',
      '  padding: 8px 18px;',
      '  font-size: 13px;',
      '  font-weight: 600;',
      '  cursor: pointer;',
      '  transition: background 0.2s, transform 0.1s;',
      '  flex: 1;',
      '  text-align: center;',
      '}',

      '.wt-btn:hover { background: rgba(74,158,255,0.28); }',
      '.wt-btn:active { transform: scale(0.96); }',

      '.wt-btn-primary {',
      '  background: rgba(74,158,255,0.28);',
      '  color: #c8dfff;',
      '}',
      '.wt-btn-primary:hover { background: rgba(74,158,255,0.42); }',

      '#wt-btn-close {',
      '  background: none;',
      '  border: none;',
      '  color: rgba(255,255,255,0.35);',
      '  font-size: 18px;',
      '  cursor: pointer;',
      '  position: absolute;',
      '  top: 12px;',
      '  right: 14px;',
      '  line-height: 1;',
      '  padding: 2px 6px;',
      '  border-radius: 4px;',
      '  transition: color 0.2s, background 0.2s;',
      '}',
      '#wt-btn-close:hover { color: #fff; background: rgba(255,255,255,0.08); }',

      /* Mobile */
      '@media (max-width: 600px) {',
      '  #wt-tooltip { padding: 18px 16px 14px; }',
      '  .wt-btn { padding: 8px 12px; font-size: 12px; }',
      '}'
    ].join('\n');
    document.head.appendChild(style);
  }

  // ─── State ──────────────────────────────────────────────────────────────────

  var currentStep = 0;
  var isActive = false;
  var resizeTimer = null;

  // ─── Build DOM ──────────────────────────────────────────────────────────────

  function buildOverlay() {
    if (document.getElementById('walkthrough-overlay')) return;

    injectStyles();

    // Main overlay container
    var overlay = document.createElement('div');
    overlay.id = 'walkthrough-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'false');
    overlay.setAttribute('aria-label', 'Guided tour overlay');

    // Scrim (click outside to close)
    var scrim = document.createElement('div');
    scrim.id = 'wt-scrim';
    overlay.appendChild(scrim);

    // Highlight ring
    var highlight = document.createElement('div');
    highlight.id = 'wt-highlight';
    overlay.appendChild(highlight);

    // Tooltip
    var tooltip = document.createElement('div');
    tooltip.id = 'wt-tooltip';
    tooltip.setAttribute('role', 'region');

    tooltip.innerHTML = [
      '<button id="wt-btn-close" aria-label="Close tour">✕</button>',
      '<div id="wt-step-counter">Step 1 of ' + STEPS.length + '</div>',
      '<h3 id="wt-tooltip-title"></h3>',
      '<p id="wt-tooltip-body"></p>',
      '<div id="wt-tooltip-buttons">',
      '  <button class="wt-btn" id="wt-btn-back">← Back</button>',
      '  <button class="wt-btn wt-btn-primary" id="wt-btn-next">Next →</button>',
      '</div>',
      '<div id="wt-tooltip-arrow"></div>'
    ].join('');

    overlay.appendChild(tooltip);
    document.body.appendChild(overlay);

    // Events
    scrim.addEventListener('click', function () { WalkthroughController.stop(); });
    document.getElementById('wt-btn-close').addEventListener('click', function () { WalkthroughController.stop(); });
    document.getElementById('wt-btn-next').addEventListener('click', handleNext);
    document.getElementById('wt-btn-back').addEventListener('click', handleBack);
    document.addEventListener('keydown', handleKeydown);
    window.addEventListener('resize', handleResize);
  }

  // ─── Navigation ─────────────────────────────────────────────────────────────

  function handleNext() {
    if (currentStep < STEPS.length - 1) {
      currentStep++;
      renderStep(currentStep);
    } else {
      WalkthroughController.stop();
    }
  }

  function handleBack() {
    if (currentStep > 0) {
      currentStep--;
      renderStep(currentStep);
    }
  }

  function handleKeydown(e) {
    if (!isActive) return;
    switch (e.key) {
      case 'Escape':
        WalkthroughController.stop();
        break;
      case 'ArrowRight':
        e.preventDefault();
        handleNext();
        break;
      case 'ArrowLeft':
        e.preventDefault();
        handleBack();
        break;
      default:
        break;
    }
  }

  function handleResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (isActive) positionTooltip(currentStep);
    }, 80);
  }

  // ─── Rendering ──────────────────────────────────────────────────────────────

  function findTarget(selector) {
    return document.querySelector(selector);
  }

  function getTargetRect(el) {
    var rect = el.getBoundingClientRect();
    var scrollY = window.scrollY || window.pageYOffset;
    var scrollX = window.scrollX || window.pageXOffset;
    return {
      top: rect.top,
      left: rect.left,
      bottom: rect.bottom,
      right: rect.right,
      width: rect.width,
      height: rect.height,
      pageTop: rect.top + scrollY,
      pageLeft: rect.left + scrollX
    };
  }

  function scrollToTarget(el) {
    var rect = el.getBoundingClientRect();
    var viewH = window.innerHeight;
    var MARGIN = 80;

    if (rect.top < MARGIN || rect.bottom > viewH - MARGIN) {
      var targetScrollY = window.scrollY + rect.top - viewH / 2 + rect.height / 2;
      window.scrollTo({ top: Math.max(0, targetScrollY), behavior: 'smooth' });
    }
  }

  function positionHighlight(rect) {
    var highlight = document.getElementById('wt-highlight');
    var PAD = 6;
    highlight.style.top = (rect.top - PAD) + 'px';
    highlight.style.left = (rect.left - PAD) + 'px';
    highlight.style.width = (rect.width + PAD * 2) + 'px';
    highlight.style.height = (rect.height + PAD * 2) + 'px';
  }

  function positionTooltip(stepIndex) {
    var step = STEPS[stepIndex];
    var target = findTarget(step.target);
    if (!target) return;

    var rect = target.getBoundingClientRect();
    var tooltip = document.getElementById('wt-tooltip');
    var arrow = document.getElementById('wt-tooltip-arrow');
    var viewW = window.innerWidth;
    var viewH = window.innerHeight;
    var MARGIN = 12;
    var ARROW_HALF = 6;

    positionHighlight(rect);

    // Determine tooltip dimensions (approximate before paint)
    var tooltipW = Math.min(420, viewW * 0.92);
    var tooltipH = tooltip.offsetHeight || 220;

    var position = step.position || 'bottom';

    // If preferred position doesn't fit, flip
    if (position === 'bottom' && rect.bottom + tooltipH + MARGIN > viewH) {
      position = 'top';
    }
    if (position === 'top' && rect.top - tooltipH - MARGIN < 0) {
      position = 'bottom';
    }

    var tooltipTop, tooltipLeft, arrowTop, arrowLeft, arrowTransform;

    if (position === 'bottom') {
      tooltipTop = rect.bottom + MARGIN;
      // Try to center on target, clamp to viewport
      tooltipLeft = rect.left + rect.width / 2 - tooltipW / 2;
      tooltipLeft = Math.max(MARGIN, Math.min(tooltipLeft, viewW - tooltipW - MARGIN));
      // Arrow: top center of tooltip, pointing up
      arrowTop = -ARROW_HALF - 1;
      arrowLeft = (rect.left + rect.width / 2) - tooltipLeft - ARROW_HALF;
      arrowLeft = Math.max(14, Math.min(arrowLeft, tooltipW - 28));
      arrowTransform = 'rotate(45deg)';
      arrow.style.borderTop = '1px solid rgba(74,158,255,0.35)';
      arrow.style.borderLeft = '1px solid rgba(74,158,255,0.35)';
      arrow.style.borderRight = '';
      arrow.style.borderBottom = '';
    } else {
      // position === 'top'
      tooltipTop = rect.top - tooltipH - MARGIN;
      tooltipTop = Math.max(MARGIN, tooltipTop);
      tooltipLeft = rect.left + rect.width / 2 - tooltipW / 2;
      tooltipLeft = Math.max(MARGIN, Math.min(tooltipLeft, viewW - tooltipW - MARGIN));
      // Arrow: bottom of tooltip, pointing down
      arrowTop = tooltipH - ARROW_HALF - 1;
      arrowLeft = (rect.left + rect.width / 2) - tooltipLeft - ARROW_HALF;
      arrowLeft = Math.max(14, Math.min(arrowLeft, tooltipW - 28));
      arrowTransform = 'rotate(225deg)';
      arrow.style.borderTop = '1px solid rgba(74,158,255,0.35)';
      arrow.style.borderLeft = '1px solid rgba(74,158,255,0.35)';
      arrow.style.borderRight = '';
      arrow.style.borderBottom = '';
    }

    tooltip.style.top = tooltipTop + 'px';
    tooltip.style.left = tooltipLeft + 'px';
    tooltip.style.width = tooltipW + 'px';

    arrow.style.top = arrowTop + 'px';
    arrow.style.left = arrowLeft + 'px';
    arrow.style.transform = arrowTransform;
  }

  function renderStep(stepIndex) {
    var step = STEPS[stepIndex];
    var target = findTarget(step.target);

    // Update text content
    document.getElementById('wt-step-counter').textContent =
      'Step ' + (stepIndex + 1) + ' of ' + STEPS.length;
    document.getElementById('wt-tooltip-title').textContent = step.title;
    document.getElementById('wt-tooltip-body').textContent = step.body;

    // Update buttons
    var backBtn = document.getElementById('wt-btn-back');
    var nextBtn = document.getElementById('wt-btn-next');
    backBtn.disabled = stepIndex === 0;
    backBtn.style.opacity = stepIndex === 0 ? '0.35' : '1';
    backBtn.style.pointerEvents = stepIndex === 0 ? 'none' : 'auto';
    nextBtn.textContent = stepIndex === STEPS.length - 1 ? 'Finish' : 'Next →';

    if (!target) {
      // Target not found — skip visual positioning, just show tooltip centered
      var tooltip = document.getElementById('wt-tooltip');
      tooltip.style.top = '50%';
      tooltip.style.left = '50%';
      tooltip.style.transform = 'translate(-50%, -50%)';
      return;
    } else {
      document.getElementById('wt-tooltip').style.transform = '';
    }

    // Scroll target into view first, then position
    scrollToTarget(target);

    // Position after scroll settles (smooth scroll takes ~300ms)
    setTimeout(function () {
      if (isActive) {
        positionTooltip(stepIndex);
      }
    }, 320);

    // Also position immediately for instant viewport cases
    positionTooltip(stepIndex);
  }

  // ─── Public API ─────────────────────────────────────────────────────────────

  var WalkthroughController = {
    start: function () {
      buildOverlay();

      currentStep = 0;
      isActive = true;

      var overlay = document.getElementById('walkthrough-overlay');
      var scrim = document.getElementById('wt-scrim');
      var highlight = document.getElementById('wt-highlight');
      var tooltip = document.getElementById('wt-tooltip');

      overlay.classList.add('wt-active');

      requestAnimationFrame(function () {
        scrim.classList.add('wt-scrim-visible');
        highlight.classList.add('wt-highlight-visible');
        setTimeout(function () {
          tooltip.classList.add('wt-tooltip-visible');
        }, 80);
      });

      renderStep(0);
    },

    stop: function () {
      if (!isActive) return;
      isActive = false;

      var overlay = document.getElementById('walkthrough-overlay');
      var scrim = document.getElementById('wt-scrim');
      var highlight = document.getElementById('wt-highlight');
      var tooltip = document.getElementById('wt-tooltip');

      if (tooltip) tooltip.classList.remove('wt-tooltip-visible');
      if (highlight) highlight.classList.remove('wt-highlight-visible');
      if (scrim) scrim.classList.remove('wt-scrim-visible');

      setTimeout(function () {
        if (overlay) overlay.classList.remove('wt-active');
      }, 300);
    }
  };

  window.WalkthroughController = WalkthroughController;

  // ─── Auto-wire "Tour" / "Walkthrough" button if present ─────────────────────

  function wireButton() {
    var btn = document.getElementById('btn-walkthrough');
    if (btn) {
      btn.addEventListener('click', function () {
        WalkthroughController.start();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireButton);
  } else {
    wireButton();
  }

}());
