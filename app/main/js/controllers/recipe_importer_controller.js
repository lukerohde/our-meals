import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["form", "input", "fileInput", "previewContainer", "submit", "loading", "error"]
  static values = {
    uploadUrl: String
  }

  connect() {
    this.uploadedPhotos = []
    this.isProcessing = false
    
    // Add paste handler to input only
    this.inputTarget.addEventListener('paste', (e) => this.handlePaste(e))
  }

  disconnect() {
    // Clean up event listeners
    this.inputTarget.removeEventListener('paste', (e) => this.handlePaste(e))
  }

  handleDragOver(event) {
    event.preventDefault()
    event.stopPropagation()
    this.formTarget.classList.add('drag-over')
  }
  
  handleDragLeave(event) {
    if (event.target === this.formTarget) {
      this.formTarget.classList.remove('drag-over')
    }
  }

  async handleDrop(event) {
    event.preventDefault()
    event.stopPropagation()
    this.formTarget.classList.remove('drag-over')
    
    // Check for files first
    const files = Array.from(event.dataTransfer.files).filter(file => 
      file.type.startsWith('image/')
    )
    
    if (files.length > 0) {
      for (const file of files) {
        await this.uploadPhoto(file)
      }
      return
    }
    
    // If no files, check for dragged images
    const items = Array.from(event.dataTransfer.items)
    for (const item of items) {
      if (item.type.indexOf('image/') !== -1) {
        const file = item.getAsFile()
        if (file) {
          await this.uploadPhoto(file)
        }
      }
    }
  }

  async handlePaste(event) {
    const items = event.clipboardData.items
    let hasImage = false
    
    for (let item of items) {
      if (item.type.indexOf("image") !== -1) {
        event.preventDefault() // Prevent default paste only if we have an image
        hasImage = true
        const file = item.getAsFile()
        await this.uploadPhoto(file)
      }
    }
    
    // If no images were found, let the default paste behavior happen
    if (!hasImage) {
      return
    }
  }

  async handleFileSelect(event) {
    const files = event.target.files
    for (let file of files) {
      await this.uploadPhoto(file)
    }
    this.fileInputTarget.value = '' // Clear the input
  }

  triggerFileInput() {
    this.fileInputTarget.click()
  }

  async uploadPhoto(file) {
    if (!file.type.startsWith('image/')) {
      this.showError("Only image files are allowed")
      return
    }

    const formData = new FormData()
    formData.append('photos', file)

    try {
      const response = await fetch(this.uploadUrlValue, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()
      this.uploadedPhotos.push(...data.urls)
      this.updatePhotoPreview()
    } catch (error) {
      this.showError("Failed to upload photo: " + error.message)
    }
  }

  updatePhotoPreview() {
    this.previewContainerTarget.innerHTML = this.uploadedPhotos.map((url, index) => `
      <div class="photo-preview">
        <img src="${url}" alt="Recipe photo ${index + 1}">
        <button type="button" class="remove-photo" data-index="${index}" aria-label="Remove photo">
          <i class="bi bi-trash"></i>
        </button>
      </div>
    `).join('')

    // Add click handlers for remove buttons
    this.previewContainerTarget.querySelectorAll('.remove-photo').forEach(button => {
      button.addEventListener('click', (e) => {
        const index = parseInt(e.currentTarget.dataset.index)
        this.uploadedPhotos.splice(index, 1)
        this.updatePhotoPreview()
      })
    })
  }

  async submitForm(event) {
    event.preventDefault()
    if (this.isProcessing) return

    this.isProcessing = true
    this.submitTarget.classList.add('d-none')
    this.loadingTarget.classList.remove('d-none')
    this.errorTarget.classList.add('d-none')

    try {
      // Add photo URLs to form data
      this.uploadedPhotos.forEach((url, index) => {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = `photo_${index}`
        input.value = url
        this.formTarget.appendChild(input)
      })

      const response = await fetch(this.formTarget.action, {
        method: 'POST',
        body: new FormData(this.formTarget),
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })

      const data = await response.json()
      
      if (response.ok) {
        window.location.href = data.redirect
      } else {
        throw new Error(data.message || 'Failed to import recipe')
      }
    } catch (error) {
      this.showError(error.message)
      this.submitTarget.classList.remove('d-none')
      this.loadingTarget.classList.add('d-none')
      this.isProcessing = false
    }
  }

  showError(message) {
    this.errorTarget.textContent = message
    this.errorTarget.classList.remove('d-none')
  }
}
