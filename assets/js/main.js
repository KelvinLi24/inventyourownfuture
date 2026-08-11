(() => {
  document.documentElement.classList.add('js');

  const ready = () => {
    document.body.classList.add('static-site-ready');
    wireMobileMenu();
    wireFolders();
    wireForms();
    wireLazyImages();
    wireImageFocalPoints();
    wireStaticClassicImages();
    wireStaticCarousels();
    wireStaticAccordions();
    wireStaticSummaryImages();
    wireStaticBlogImages();
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
    document.querySelectorAll('img[data-src]').forEach((img) => {
      const dataSrc = img.getAttribute('data-src');
      if (!dataSrc) return;

      if (!img.getAttribute('src')) {
        img.src = dataSrc;
      }

      if (img.complete && img.naturalWidth === 0 && !img.src.endsWith(dataSrc)) {
        img.src = dataSrc;
      }

      img.addEventListener('error', () => {
        if (img.src.endsWith(dataSrc)) return;
        img.src = dataSrc;
      }, { once: true });
    });
  };

  const parseFocalPoint = (value) => {
    if (!value) return null;

    const [xRaw, yRaw] = value.split(',');
    const x = Number.parseFloat(xRaw);
    const y = Number.parseFloat(yRaw);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;

    return {
      x: Math.max(0, Math.min(100, x * 100)),
      y: Math.max(0, Math.min(100, y * 100)),
    };
  };

  const wireImageFocalPoints = () => {
    document.querySelectorAll('img[data-image-focal-point]').forEach((img) => {
      const focalPoint = parseFocalPoint(img.getAttribute('data-image-focal-point'));
      if (!focalPoint) return;

      const position = `${focalPoint.x}% ${focalPoint.y}%`;
      img.style.objectPosition = position;
      img.style.setProperty('--image-component-focal-point', position);
    });
  };

  const wireStaticClassicImages = () => {
    document.querySelectorAll('[data-sqsp-image-classic-block-image-container].has-aspect-ratio').forEach((container) => {
      const img = container.querySelector('img[data-image-dimensions]');
      const aspectRatio = getAspectRatio(container, img);
      if (!img || !aspectRatio) return;

      const currentPadding = Number.parseFloat(container.style.paddingBottom);
      const expectedPadding = 100 / aspectRatio;
      if (!Number.isFinite(expectedPadding) || expectedPadding <= 0 || expectedPadding > 400) return;
      if (Number.isFinite(currentPadding) && currentPadding >= 5) return;

      container.classList.add('static-classic-image--restored-ratio');
      container.style.paddingBottom = `${expectedPadding}%`;
    });
  };

  const getAspectRatio = (element, img) => {
    const ratio = element.getAttribute('data-media-aspect-ratio');
    if (ratio && ratio.includes(':')) {
      const [width, height] = ratio.split(':').map(Number.parseFloat);
      if (Number.isFinite(width) && Number.isFinite(height) && height !== 0) {
        return width / height;
      }
    }

    const dimensions = img?.getAttribute('data-image-dimensions');
    if (dimensions && dimensions.includes('x')) {
      const [width, height] = dimensions.split('x').map(Number.parseFloat);
      if (Number.isFinite(width) && Number.isFinite(height) && height !== 0) {
        return width / height;
      }
    }

    return null;
  };

  const debounce = (callback) => {
    let frame = 0;

    return () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(callback);
    };
  };

  const wireStaticCarousels = () => {
    document.querySelectorAll('.user-items-list-carousel').forEach((carousel) => {
      const track = carousel.querySelector('.user-items-list-carousel__slides');
      const revealer = carousel.querySelector('.user-items-list-carousel__slides-revealer');
      const slides = Array.from(carousel.querySelectorAll('.user-items-list-carousel__slide'));
      if (!track || !revealer || slides.length < 2) return;

      const leftButton = carousel.querySelector('.user-items-list-carousel__arrow-button--left');
      const rightButton = carousel.querySelector('.user-items-list-carousel__arrow-button--right');
      const gutter = carousel.querySelector('.user-items-list-carousel__gutter') || carousel;
      const gap = Number.parseFloat(carousel.getAttribute('data-space-between-slides-value')) || 0;
      const showAdjacent = carousel.getAttribute('data-show-adjacent-slides') === 'true';
      const navigationControls = carousel.getAttribute('data-navigation-controls') || '';
      const maxColumns = Math.max(1, Number.parseInt(carousel.getAttribute('data-max-columns'), 10) || 1);
      const visibleSlides = showAdjacent || navigationControls === 'none' ? Math.min(maxColumns, slides.length) : 1;
      const isInfinite = carousel.getAttribute('data-is-infinite-enabled') === 'true';

      let currentIndex = 0;
      let slideWidth = 0;
      let step = 0;
      let activePointer = null;
      let startX = 0;
      let startY = 0;
      let startOffset = 0;
      let currentOffset = 0;
      let moved = false;

      carousel.classList.add('static-carousel');
      carousel.style.setProperty('--static-carousel-gap', `${gap}px`);
      if (navigationControls === 'none') carousel.classList.add('static-carousel--static-strip');

      const maxIndex = () => {
        if (isInfinite) return slides.length - 1;
        return Math.max(0, slides.length - visibleSlides);
      };

      const setOffset = (offset) => {
        currentOffset = offset;
        track.style.transform = `translate3d(${offset}px, 0, 0)`;
      };

      const setIndex = (nextIndex, animate = true) => {
        const lastIndex = maxIndex();
        if (isInfinite) {
          currentIndex = (nextIndex + slides.length) % slides.length;
        } else {
          currentIndex = Math.max(0, Math.min(lastIndex, nextIndex));
        }

        track.classList.toggle('static-carousel__slides--no-transition', !animate);
        setOffset(-(step * currentIndex));

        slides.forEach((slide, index) => {
          const visible = index >= currentIndex && index < currentIndex + visibleSlides;
          if (visible) {
            slide.removeAttribute('aria-hidden');
          } else {
            slide.setAttribute('aria-hidden', 'true');
          }
        });

        if (!isInfinite) {
          leftButton?.toggleAttribute('disabled', currentIndex === 0);
          rightButton?.toggleAttribute('disabled', currentIndex === lastIndex);
        }

        if (!animate) {
          window.requestAnimationFrame(() => {
            track.classList.remove('static-carousel__slides--no-transition');
          });
        }
      };

      const updateMetrics = () => {
        const totalGap = gap * (visibleSlides - 1);
        slideWidth = Math.max(1, (revealer.clientWidth - totalGap) / visibleSlides);
        step = slideWidth + gap;
        carousel.style.setProperty('--static-carousel-slide-width', `${slideWidth}px`);
        setIndex(currentIndex, false);
      };

      slides.forEach((slide) => {
        slide.style.transform = '';
        slide.removeAttribute('aria-hidden');

        const mediaInner = slide.querySelector('.user-items-list-carousel__media-inner');
        const media = slide.querySelector('.user-items-list-carousel__media');
        const aspectRatio = mediaInner ? getAspectRatio(mediaInner, media) : null;
        const mediaSrc = (media?.getAttribute('data-src') || media?.getAttribute('src') || '').toLowerCase();
        const isLogoLikeMedia = /\/invent(?:-\d+)?\.png$/.test(mediaSrc) || navigationControls === 'none';

        if (mediaInner && aspectRatio) {
          mediaInner.style.setProperty('--static-media-aspect-ratio', String(aspectRatio));
        }

        if (media && isLogoLikeMedia) {
          media.classList.add('static-carousel__media--contain');
          media.style.objectFit = 'contain';
          media.style.height = '100%';
          media.style.width = '100%';
        }
      });

      leftButton?.addEventListener('click', (event) => {
        event.preventDefault();
        setIndex(currentIndex - 1);
      });

      rightButton?.addEventListener('click', (event) => {
        event.preventDefault();
        setIndex(currentIndex + 1);
      });

      gutter.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowLeft') {
          event.preventDefault();
          setIndex(currentIndex - 1);
        }

        if (event.key === 'ArrowRight') {
          event.preventDefault();
          setIndex(currentIndex + 1);
        }
      });

      revealer.addEventListener('pointerdown', (event) => {
        if (event.pointerType === 'mouse' && event.button !== 0) return;
        if (event.target.closest('.user-items-list-carousel__arrow-button')) return;

        activePointer = event.pointerId;
        startX = event.clientX;
        startY = event.clientY;
        startOffset = currentOffset;
        moved = false;
        carousel.classList.add('static-carousel--dragging');
        revealer.setPointerCapture(activePointer);
      });

      revealer.addEventListener('pointermove', (event) => {
        if (activePointer !== event.pointerId) return;

        const deltaX = event.clientX - startX;
        const deltaY = event.clientY - startY;
        if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 12) return;

        if (Math.abs(deltaX) > 4) moved = true;
        if (moved && event.cancelable) event.preventDefault();

        track.classList.add('static-carousel__slides--no-transition');
        setOffset(startOffset + deltaX);
      });

      const endDrag = (event) => {
        if (activePointer !== event.pointerId) return;

        const deltaX = event.clientX - startX;
        const threshold = Math.min(80, Math.max(24, slideWidth * 0.16));
        activePointer = null;
        carousel.classList.remove('static-carousel--dragging');
        track.classList.remove('static-carousel__slides--no-transition');

        if (moved && Math.abs(deltaX) > threshold) {
          setIndex(currentIndex + (deltaX < 0 ? 1 : -1));
        } else {
          setIndex(currentIndex);
        }

        if (moved) {
          carousel.dataset.staticDragPreventClick = 'true';
          window.setTimeout(() => {
            delete carousel.dataset.staticDragPreventClick;
          }, 120);
        }
      };

      revealer.addEventListener('pointerup', endDrag);
      revealer.addEventListener('pointercancel', endDrag);
      carousel.addEventListener('click', (event) => {
        if (!carousel.dataset.staticDragPreventClick) return;
        if (!event.target.closest('a')) return;

        event.preventDefault();
        event.stopPropagation();
      }, true);

      updateMetrics();
      window.addEventListener('resize', debounce(updateMetrics));
    });
  };

  const wireStaticAccordions = () => {
    document.querySelectorAll('.accordion-block').forEach((accordion) => {
      const container = accordion.querySelector('.accordion-items-container');
      const buttons = Array.from(accordion.querySelectorAll('.accordion-item__click-target'));
      if (!container || !buttons.length) return;

      accordion.classList.add('static-accordion-ready');
      const allowMultiple = container.getAttribute('data-should-allow-multiple-open-items') === 'true';

      const setOpen = (button, open) => {
        const item = button.closest('.accordion-item');
        const dropdownId = button.getAttribute('aria-controls');
        const dropdown = dropdownId ? accordion.querySelector(`#${window.CSS.escape(dropdownId)}`) : null;
        if (!item || !dropdown) return;

        button.setAttribute('aria-expanded', String(open));
        item.setAttribute('data-is-open', String(open));
        dropdown.classList.toggle('accordion-item__dropdown--open', open);
        dropdown.style.setProperty('--static-accordion-panel-height', `${dropdown.scrollHeight}px`);
      };

      buttons.forEach((button) => {
        setOpen(button, button.getAttribute('aria-expanded') === 'true');

        button.addEventListener('click', (event) => {
          event.preventDefault();
          const shouldOpen = button.getAttribute('aria-expanded') !== 'true';
          if (shouldOpen && !allowMultiple) {
            buttons.forEach((otherButton) => {
              if (otherButton !== button) setOpen(otherButton, false);
            });
          }
          setOpen(button, shouldOpen);
        });

        button.addEventListener('keydown', (event) => {
          if (event.key !== 'Escape') return;
          setOpen(button, false);
          button.focus();
        });
      });

      window.addEventListener('resize', debounce(() => {
        buttons.forEach((button) => {
          if (button.getAttribute('aria-expanded') === 'true') setOpen(button, true);
        });
      }));
    });
  };

  const wireStaticSummaryImages = () => {
    document.querySelectorAll('.summary-block-wrapper').forEach((wrapper) => {
      wrapper.classList.add('static-summary-grid');
      wrapper.querySelectorAll('.summary-item-list').forEach((list) => {
        list.style.marginBottom = '';
      });

      wrapper.querySelectorAll('.summary-item').forEach((item) => {
        item.style.width = '';
        item.style.float = '';
        item.style.clear = '';
        item.style.marginRight = '';
        item.style.marginBottom = '';
      });

      wrapper.querySelectorAll('.summary-thumbnail').forEach((thumbnail) => {
        thumbnail.style.paddingBottom = '';
        thumbnail.style.overflow = '';
      });

      wrapper.querySelectorAll('.summary-thumbnail-image').forEach((img) => {
        img.style.top = '';
        img.style.left = '';
        img.style.width = '';
        img.style.height = '';
        img.style.objectFit = '';
      });
    });
  };

  const wireStaticBlogImages = () => {
    document.querySelectorAll('.blog-masonry-wrapper').forEach((wrapper) => {
      const articles = Array.from(wrapper.querySelectorAll('.blog-item'));
      if (!articles.length) return;

      wrapper.classList.add('static-blog-list');

      const normalize = () => {
        wrapper.style.height = '';

        articles.forEach((article) => {
          article.style.position = '';
          article.style.width = '';
          article.style.transform = '';

          const imageLink = article.querySelector('.blog-image-wrapper .image-wrapper');
          if (imageLink) {
            imageLink.style.height = 'auto';
            imageLink.style.overflow = 'visible';
          }

          article.querySelectorAll('.blog-image-wrapper img').forEach((img) => {
            img.style.display = 'block';
            img.style.position = 'static';
            img.style.width = '100%';
            img.style.height = 'auto';
            img.style.objectFit = 'contain';

            const dataSrc = img.getAttribute('data-src');
            if (dataSrc && img.complete && img.naturalWidth === 0 && !img.src.endsWith(dataSrc)) {
              img.src = dataSrc;
            }
          });
        });
      };

      normalize();
      window.addEventListener('load', normalize, { once: true });
      window.setTimeout(normalize, 600);
      window.setTimeout(normalize, 1800);
      window.addEventListener('resize', debounce(normalize));
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ready);
  } else {
    ready();
  }
})();
