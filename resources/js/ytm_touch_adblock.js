/**
 * DuckDock YouTube Music Touch AdBlock, Inactivity Bypass & Media Bridge
 */
(function () {
    'use strict';

    if (window.__duckdock_adblock_initialized) return;
    window.__duckdock_adblock_initialized = true;

    console.log('[DuckDock] YTM Touch AdBlock & Media Watcher initialized.');

    // 1. Подавление рекламы и авто-скип
    function handleAdBypass() {
        const adShowing = document.querySelector('.ad-showing, .ad-interrupting, .video-ads.ytp-ad-module');
        const video = document.querySelector('video');

        if (video) {
            if (adShowing) {
                try {
                    video.muted = true;
                    video.playbackRate = 16.0;
                    if (Number.isFinite(video.duration) && video.duration > 0) {
                        video.currentTime = video.duration;
                    }
                } catch (e) {
                    console.debug('[DuckDock] Ad fast-forward exception:', e);
                }
            }

            // Автоклик по кнопкам пропуска рекламы
            const skipButtons = [
                '.ytp-ad-skip-button',
                '.ytp-ad-skip-button-modern',
                '.videoAdUiSkipButton',
                '.ytp-skip-ad-button',
                'button.ytp-ad-skip-button-modern',
                '.ytp-ad-skip-button-container button'
            ];
            for (const selector of skipButtons) {
                const btn = document.querySelector(selector);
                if (btn && typeof btn.click === 'function') {
                    btn.click();
                }
            }
        }

        // Удаление промо-баннеров и модальных окон премиума
        const promos = document.querySelectorAll(
            'ytmusic-mealbar-promo-renderer, ytmusic-upsell-dialog-renderer, ytd-mealbar-promo-renderer'
        );
        promos.forEach(el => el.remove());

        // Подтверждение диалога "Вы еще смотрите?" / Inactivity prompt
        const youThere = document.querySelector('ytmusic-you-there-renderer');
        if (youThere) {
            const confirmBtn = youThere.querySelector('button, yt-button-renderer');
            if (confirmBtn && typeof confirmBtn.click === 'function') {
                confirmBtn.click();
            } else {
                youThere.remove();
            }
        }
    }

    // 2. Снятие состояния медиаплеера (Title, Artist, IsPlaying)
    window.__duckdock_get_media_state = function () {
        const titleEl = document.querySelector('ytmusic-player-bar .title') ||
                        document.querySelector('.title.ytmusic-player-bar') ||
                        document.querySelector('ytmusic-player-queue-item[selected] .song-title');

        const bylineEl = document.querySelector('ytmusic-player-bar .byline') ||
                         document.querySelector('.byline.ytmusic-player-bar') ||
                         document.querySelector('ytmusic-player-queue-item[selected] .byline');

        const playPauseBtn = document.querySelector('#play-pause-button');
        const video = document.querySelector('video');

        const title = titleEl ? (titleEl.textContent || titleEl.innerText || '').trim() : '';
        const artist = bylineEl ? (bylineEl.textContent || bylineEl.innerText || '').trim() : '';

        let isPlaying = false;
        if (video) {
            isPlaying = !video.paused && !video.ended && video.readyState > 2;
        } else if (playPauseBtn) {
            const label = playPauseBtn.getAttribute('aria-label') || '';
            isPlaying = label.toLowerCase().includes('pause') || label.toLowerCase().includes('пауза');
        }

        return {
            title: title || (video && !video.paused ? 'YouTube Media' : 'No Media'),
            artist: artist || '',
            is_playing: isPlaying
        };
    };

    // 3. Управление воспроизведением плеера из внешней среды
    window.__duckdock_media_action = function (action) {
        if (action === 'toggle_play' || action === 'play_pause') {
            const btn = document.querySelector('#play-pause-button');
            if (btn && typeof btn.click === 'function') {
                btn.click();
                return true;
            }
            const video = document.querySelector('video');
            if (video) {
                if (video.paused) video.play(); else video.pause();
                return true;
            }
        } else if (action === 'next') {
            const btn = document.querySelector(
                '.next-button.ytmusic-player-bar, ytmusic-player-bar .next-button, #next-button'
            );
            if (btn && typeof btn.click === 'function') {
                btn.click();
                return true;
            }
        } else if (action === 'prev' || action === 'previous') {
            const btn = document.querySelector(
                '.previous-button.ytmusic-player-bar, ytmusic-player-bar .previous-button, #previous-button'
            );
            if (btn && typeof btn.click === 'function') {
                btn.click();
                return true;
            }
        }
        return false;
    };

    // Запуск таймера непрерывного мониторинга
    setInterval(handleAdBypass, 300);

    // MutationObserver для мгновенной реакции на рекламу
    const observer = new MutationObserver(() => {
        handleAdBypass();
    });

    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            if (document.body) {
                observer.observe(document.body, { childList: true, subtree: true });
            }
        });
    }
})();
