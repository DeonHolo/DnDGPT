(() => {
  const views = {conversation: document.getElementById('conversation-view'), standalone: document.getElementById('standalone-view')};
  const buttons = [...document.querySelectorAll('[data-view]')];
  buttons.forEach(button => button.addEventListener('click', () => {
    buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    Object.entries(views).forEach(([name, view]) => { view.hidden = name !== button.dataset.view; });
    if (window.ScrollTrigger) ScrollTrigger.refresh();
  }));
  const panels = [...document.querySelectorAll('.feature-panels details')];
  panels.forEach(panel => panel.addEventListener('toggle', () => {
    if (panel.open) panels.filter(other => other !== panel).forEach(other => { other.open = false; });
    if (window.ScrollTrigger) ScrollTrigger.refresh();
  }));
  if (!window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);
  const media = gsap.matchMedia();
  media.add('(prefers-reduced-motion: no-preference)', () => {
    gsap.from('.hero-art', {opacity: 0, y: 24, duration: 1.2, ease: 'power2.out'});
    gsap.fromTo('#conversation-view', {scale: .8}, {scale: 1, ease: 'none', scrollTrigger: {trigger: '.capture-gallery', start: 'top 95%', end: 'top 25%', scrub: .8}});
    gsap.to('.hero-art img', {yPercent: 9, ease: 'none', scrollTrigger: {trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 1}});
    gsap.from('.origin-art img', {scale: 1.12, ease: 'none', scrollTrigger: {trigger: '.origin', start: 'top bottom', end: 'center center', scrub: 1}});
    gsap.fromTo('.clover-grove', {y: 16}, {y: -8, ease: 'none', scrollTrigger: {trigger: '.journey', start: 'top bottom', end: 'bottom top', scrub: 1}});
  });
  media.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', () => {
    ScrollTrigger.create({trigger: '.journey-copy', start: 'top 100px', endTrigger: '.journey-entries', end: 'bottom bottom-=80px', pin: true, pinSpacing: false});
  });
})();
