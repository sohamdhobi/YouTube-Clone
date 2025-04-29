/**
 * Watch Time Tracker for Video Recommendation Engine
 * 
 * Tracks the amount of time a user spends watching a video and periodically
 * sends updates to the server to improve recommendations and watch statistics.
 */

class WatchTimeTracker {
    constructor(options = {}) {
        // Default configuration
        this.config = {
            videoSelector: '#video-player video',  // Selector for video element
            updateInterval: 10000,                 // How often to send updates (ms)
            recordThreshold: 5000,                 // Minimum watch time to record (ms)
            submitUrl: '/videos/update-watch-time/',  // URL to send updates
            csrfToken: null,                       // CSRF token for POST requests
            videoId: null,                         // ID of the current video
            ...options
        };
        
        // State variables
        this.watchTime = 0;        // Total seconds watched
        this.lastUpdate = 0;       // Time of last update
        this.isPlaying = false;    // Whether video is currently playing
        this.startTime = null;     // When current watching session started
        this.videoElement = null;  // The video DOM element
        this.updateTimer = null;   // Timer for periodic updates
        
        // Initialize tracker
        this.init();
    }
    
    /**
     * Initialize the tracker
     */
    init() {
        // Find video element
        this.videoElement = document.querySelector(this.config.videoSelector);
        
        if (!this.videoElement) {
            console.error('Video element not found with selector:', this.config.videoSelector);
            return;
        }
        
        // Add event listeners
        this.videoElement.addEventListener('play', this.handlePlay.bind(this));
        this.videoElement.addEventListener('pause', this.handlePause.bind(this));
        this.videoElement.addEventListener('ended', this.handleEnded.bind(this));
        
        // Set up timer for periodic updates
        this.updateTimer = setInterval(this.sendUpdate.bind(this), this.config.updateInterval);
        
        // Send initial update and record view
        setTimeout(() => {
            this.sendUpdate(true);
        }, 1000);
        
        // Clean up on page unload
        window.addEventListener('beforeunload', this.handleUnload.bind(this));
        
        console.log('Watch time tracker initialized');
    }
    
    /**
     * Handle video play event
     */
    handlePlay() {
        this.isPlaying = true;
        this.startTime = Date.now();
        console.log('Video playback started');
    }
    
    /**
     * Handle video pause event
     */
    handlePause() {
        if (this.isPlaying && this.startTime) {
            const currentTime = Date.now();
            const sessionTime = (currentTime - this.startTime) / 1000; // Convert to seconds
            
            this.watchTime += sessionTime;
            this.isPlaying = false;
            this.startTime = null;
            
            console.log(`Video paused after ${sessionTime.toFixed(1)} seconds`);
            
            // Send update on pause if it's been long enough since last update
            if (currentTime - this.lastUpdate > this.config.recordThreshold) {
                this.sendUpdate();
            }
        }
    }
    
    /**
     * Handle video ended event
     */
    handleEnded() {
        this.handlePause(); // Same logic as pause
        this.sendUpdate(true); // Force update when video ends
        console.log('Video playback ended');
    }
    
    /**
     * Handle page unload event
     */
    handleUnload() {
        // Update watch time one last time before page unloads
        if (this.isPlaying && this.startTime) {
            const sessionTime = (Date.now() - this.startTime) / 1000;
            this.watchTime += sessionTime;
        }
        
        // Send final update synchronously
        this.sendUpdate(true, true);
        
        // Clear timer
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
    }
    
    /**
     * Send watch time update to server
     * 
     * @param {boolean} force Force update even if below threshold
     * @param {boolean} sync Send synchronously (for page unload)
     */
    sendUpdate(force = false, sync = false) {
        // Update current watch session if video is playing
        if (this.isPlaying && this.startTime) {
            const sessionTime = (Date.now() - this.startTime) / 1000;
            this.watchTime += sessionTime;
            this.startTime = Date.now(); // Reset start time for next calculation
        }
        
        // Only send if we have watch time or are forcing an update
        if (this.watchTime > 0 || force) {
            const currentTime = Date.now();
            
            // Check if we should send an update based on threshold
            if (force || currentTime - this.lastUpdate >= this.config.recordThreshold) {
                this.lastUpdate = currentTime;
                
                const data = new FormData();
                data.append('video_id', this.config.videoId);
                data.append('watch_time', Math.round(this.watchTime));
                data.append('csrfmiddlewaretoken', this.config.csrfToken);
                
                if (sync) {
                    // Synchronous request for page unload
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', this.config.submitUrl, false); // false = synchronous
                    xhr.send(data);
                } else {
                    // Asynchronous request
                    fetch(this.config.submitUrl, {
                        method: 'POST',
                        body: data,
                        credentials: 'same-origin'
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Watch time update successful:', data);
                    })
                    .catch(error => {
                        console.error('Error updating watch time:', error);
                    });
                }
                
                console.log(`Watch time update sent: ${Math.round(this.watchTime)} seconds`);
            }
        }
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        // Remove event listeners
        if (this.videoElement) {
            this.videoElement.removeEventListener('play', this.handlePlay);
            this.videoElement.removeEventListener('pause', this.handlePause);
            this.videoElement.removeEventListener('ended', this.handleEnded);
        }
        
        // Clear timer
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        // Remove unload handler
        window.removeEventListener('beforeunload', this.handleUnload);
        
        // Send final update
        this.handleUnload();
        
        console.log('Watch time tracker destroyed');
    }
} 