// Scripts de la page d'accueil : texte defilant du hero + carrousel des formations.
// Extraits du gabarit third_pages/home.html — aucun code Django, pur JS.

  const termes = ["Bienvenue sur Yu-Paan", "Plateforme de gestion des formations aux métiers"];
  let i = 0, j = 0, suppression = false;

  function ecrire() {
    const el = document.getElementById('typewriter');
    const mot = termes[i];

    if (!suppression) {
      el.textContent = mot.substring(0, j++);
      if (j > mot.length) { suppression = true; setTimeout(ecrire, 1500); return; }
    } else {
      el.textContent = mot.substring(0, j--);
      if (j < 0) { suppression = false; i = (i + 1) % termes.length; j = 0; }
    }
    setTimeout(ecrire, suppression ? 50 : 100);
  }

  ecrire();
(function () {
    const track = document.getElementById('carousel-track');
    const prevBtn = document.getElementById('carousel-prev');
    const nextBtn = document.getElementById('carousel-next');
    const dotsContainer = document.getElementById('carousel-dots');

    if (!track) return;

    const cards = track.querySelectorAll('.carousel-card');
    if (!cards.length) return;

    let current = 0;

    // Calcul du nombre de cartes visibles selon la largeur
    function visibleCount() {
        const w = document.getElementById('carousel-wrapper').offsetWidth;
        if (w >= 1024) return 3;
        if (w >= 640) return 2;
        return 1;
    }

    function cardWidth() {
        // largeur carte + gap (gap-6 = 24px)
        return cards[0].offsetWidth + 24;
    }

    function maxIndex() {
        return Math.max(0, cards.length - visibleCount());
    }

    // Création des dots
    function buildDots() {
        dotsContainer.innerHTML = '';
        const total = maxIndex() + 1;
        for (let i = 0; i < total; i++) {
            const d = document.createElement('button');
            d.className = 'h-2.5 rounded-full transition-all duration-300 ' +
                (i === current ? 'w-6 bg-bsb-primary' : 'w-2.5 bg-gray-300');
            d.setAttribute('aria-label', 'Aller à la formation ' + (i + 1));
            d.addEventListener('click', () => goTo(i));
            dotsContainer.appendChild(d);
        }
    }

    function updateDots() {
        const dots = dotsContainer.querySelectorAll('button');
        dots.forEach((d, i) => {
            d.className = 'rounded-full transition-all duration-300 h-2.5 ' +
                (i === current ? 'w-6 bg-bsb-primary' : 'w-2.5 bg-gray-300');
        });
    }

    function goTo(index) {
        current = Math.max(0, Math.min(index, maxIndex()));
        track.style.transform = `translateX(-${current * cardWidth()}px)`;
        updateDots();
        prevBtn.disabled = current === 0;
        nextBtn.disabled = current === maxIndex();
        prevBtn.classList.toggle('opacity-40', current === 0);
        nextBtn.classList.toggle('opacity-40', current === maxIndex());
    }

    prevBtn.addEventListener('click', () => goTo(current - 1));
    nextBtn.addEventListener('click', () => goTo(current + 1));

    // Touch / swipe
    let startX = 0;
    track.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, { passive: true });
    track.addEventListener('touchend', e => {
        const diff = startX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) goTo(diff > 0 ? current + 1 : current - 1);
    });

    // Init & resize
    function init() {
        buildDots();
        goTo(0);
    }

    init();
    window.addEventListener('resize', () => { buildDots(); goTo(Math.min(current, maxIndex())); });
})();
