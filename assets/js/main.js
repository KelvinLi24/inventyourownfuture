(() => {
  document.documentElement.classList.add('js');

  const ready = () => {
    document.body.classList.add('static-site-ready');
    wireMobileMenu();
    wireFolders();
    wireForms();
    wireLazyImages();
  };

  const wireMobileMenu = () => {
    const toggles = document.querySelectorAll('.header-burger-btn, .burger, [data-test="header-burger"]');
    const menu = document.querySelector('.header-menu');
    if (!toggles.length || !menu) return;

    const setOpen = (open) => {
      document.body.classList.toggle('header-menu-open', open);
      menu.classList.toggle('menu-open', open);
      toggles.forEach((toggle) => {
        toggle.setAttribute('aria-expanded', String(open));
      });
    };

    toggles.forEach((toggle) => {
      toggle.setAttribute('aria-controls', menu.id || 'header-menu');
      toggle.addEventListener('click', (event) => {
        event.preventDefault();
        setOpen(!document.body.classList.contains('header-menu-open'));
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') setOpen(false);
    });

    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => setOpen(false));
    });
  };

  const wireFolders = () => {
    document.querySelectorAll('.header-nav-folder-title, [data-folder-id], [data-action="back"]').forEach((control) => {
      control.addEventListener('click', (event) => {
        const targetId = control.getAttribute('aria-controls') || control.getAttribute('data-folder-id');
        if (!targetId) return;
        const folder = document.getElementById(targetId.replace(/^\//, '')) || document.querySelector(`[data-folder="${targetId}"]`);
        if (!folder) return;
        event.preventDefault();
        const expanded = control.getAttribute('aria-expanded') === 'true';
        control.setAttribute('aria-expanded', String(!expanded));
        folder.hidden = expanded;
      });
    });
  };

  const wireForms = () => {
    document.querySelectorAll('form.react-form-contents, form').forEach((form) => {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        let message = form.querySelector('.static-form-message');
        if (!message) {
          message = document.createElement('p');
          message.className = 'static-form-message';
          form.appendChild(message);
        }
        message.textContent = 'This static copy preserves the form layout. Connect this form to a static form provider before publishing submissions.';
      });
    });
  };

  const wireLazyImages = () => {
    document.querySelectorAll('img[data-src]:not([src])').forEach((img) => {
      img.src = img.getAttribute('data-src');
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ready);
  } else {
    ready();
  }
})();
