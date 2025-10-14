import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { timeout } from 'rxjs/operators';

interface Toast {
  type: 'success' | 'error';
  title: string;
  message: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./styles.css']
})
export class AppComponent {
  fileToUpload: File | null = null;
  extractedData: any = null;
  errorMessage: string | null = null;
  loading = false;
  toast: Toast | null = null;
  isDragOver = false;
  copying = false;

  constructor(private http: HttpClient) {}

  prettySize(bytes: number): string {
    if (!bytes && bytes !== 0) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let val = bytes;
    while (val >= 1024 && i < units.length - 1) {
      val /= 1024;
      i++;
    }
    return val.toFixed(1) + ' ' + units[i];
  }

  setFile(event: Event): void {
    const inputEl = event.target as HTMLInputElement;
    const file = inputEl.files && inputEl.files[0];
    console.log('File selected via input:', file);
    this.fileToUpload = file || null;
  }

  clearFile(): void {
    this.fileToUpload = null;
    this.extractedData = null;
    this.errorMessage = null;
    const fi = document.getElementById('fileInput') as HTMLInputElement;
    if (fi) fi.value = '';
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
    if (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files.length) {
      const file = event.dataTransfer.files[0];
      console.log('File dropped:', file);
      this.fileToUpload = file;
    }
  }

  onDropzoneKeydown(event: KeyboardEvent): void {
    if (event && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      const fi = document.getElementById('fileInput') as HTMLInputElement;
      if (fi) fi.click();
    }
  }

  private showToast(type: 'success' | 'error', title: string, message: string, ms: number = 2500): Promise<void> {
    this.toast = { type, title, message };
    return new Promise(resolve => setTimeout(() => {
      this.toast = null;
      resolve();
    }, ms));
  }

  uploadResume(): void {
    if (!this.fileToUpload) {
      this.errorMessage = "Please select a file first.";
      this.showToast('error', 'Missing File', 'Please choose a resume to extract.');
      return;
    }

    const formData = new FormData();
    formData.append('resume_file', this.fileToUpload);

    this.extractedData = null;
    this.errorMessage = null;
    this.loading = true;

    const endpoint = 'http://127.0.0.1:8000/extract/';

    this.http.post(endpoint, formData)
      .pipe(timeout(30000)) // 30 second timeout
      .subscribe({
        next: (response: any) => {
          this.extractedData = response;
          this.showToast('success', 'Success', 'Resume data extracted successfully.').then(() => {
            this.loading = false;
          });
        },
        error: (error: any) => {
          const detail = (error && error.error && (error.error.detail || error.error.error)) || 'Could not connect to the server.';
          this.errorMessage = "An error occurred: " + detail;
          this.showToast('error', 'Error', detail).then(() => {
            this.loading = false;
          });
        }
      });
  }

  copyJson(): void {
    if (!this.extractedData) {
      this.showToast('error', 'Nothing to copy', 'Please extract data first.');
      return;
    }
    const text = JSON.stringify(this.extractedData, null, 2);
    this.copying = true;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => {
          this.showToast('success', 'Copied', 'JSON copied to clipboard.');
        })
        .catch(() => {
          this.showToast('error', 'Copy Failed', 'Clipboard not available.');
        })
        .finally(() => {
          this.copying = false;
        });
    } else {
      this.showToast('error', 'Copy Failed', 'Clipboard not available.');
      this.copying = false;
    }
  }
}