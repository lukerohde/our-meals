/**
 * Utility for showing toast notifications
 * Supports both Bootstrap toasts and Django messages
 */

export function showToast(message, type = 'success') {
    const toast = document.createElement('div')
    toast.className = 'position-fixed bottom-0 end-0 p-3'
    toast.style.zIndex = '11'

    // Map Django message tags to Bootstrap classes
    const typeMap = {
        'debug': 'secondary',
        'info': 'info',
        'success': 'success',
        'warning': 'warning',
        'error': 'danger'
    }
    
    const bootstrapType = typeMap[type] || type
    const icon = type === 'success' ? 'check-circle' : 
                type === 'error' ? 'x-circle' :
                type === 'warning' ? 'exclamation-circle' : 'info-circle'

    toast.innerHTML = `
        <div class="toast align-items-center text-white bg-${bootstrapType} border-0" 
             role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${icon} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `

    document.body.appendChild(toast)
    const bsToast = new bootstrap.Toast(toast.querySelector('.toast'), {
        delay: 10000  // Keep toast visible for 10 seconds
    })
    bsToast.show()

    // Remove the element after the toast is hidden
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast)
    })
}

// Listen for show-toast events
document.addEventListener('show-toast', (event) => {
    const { message, type } = event.detail
    showToast(message, type)
})
