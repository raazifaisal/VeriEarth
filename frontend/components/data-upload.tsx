'use client';

import { useState, useCallback } from 'react';
import { useOrganization } from '@/lib/organization-context';
import { ingestionApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Label } from './ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Upload, FileText, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const ENTITY_TYPES = [
  { value: 'facilities', label: 'Facilities' },
  { value: 'shipments', label: 'Shipments' },
  { value: 'routes', label: 'Routes' },
  { value: 'suppliers', label: 'Suppliers' },
  { value: 'products', label: 'Products' },
];

export function DataUpload() {
  const { orgId } = useOrganization();
  const [entityType, setEntityType] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [previewData, setPreviewData] = useState<any[] | null>(null);
  const [uploadResult, setUploadResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith('.csv')) {
      setFile(droppedFile);
      setUploadResult(null);
      setPreviewData(null);
    } else {
      toast.error('Please upload a CSV file');
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadResult(null);
      setPreviewData(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !entityType || !orgId) {
      toast.error('Please select a file and entity type');
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      const uploadResponse = await ingestionApi.upload(file, entityType, orgId);

      const preview = await ingestionApi.preview(file, entityType);
      setPreviewData(preview.slice(0, 5));

      clearInterval(progressInterval);
      setProgress(100);

      const importResult = await ingestionApi.import(file, entityType, orgId);

      if (importResult.status === 'success') {
        setUploadResult({
          success: true,
          message: `Successfully imported ${importResult.rows_imported} rows`,
        });
        toast.success(`Imported ${importResult.rows_imported} rows successfully`);
      } else {
        setUploadResult({
          success: false,
          message: `Failed to import ${importResult.rows_failed || 0} rows`,
        });
        toast.error('Import completed with errors');
      }
    } catch (error) {
      setUploadResult({
        success: false,
        message: 'Upload failed. Please try again.',
      });
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Data</CardTitle>
        <CardDescription>
          Upload CSV files to import facilities, shipments, routes, and more
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label>Entity Type</Label>
          <Select value={entityType} onValueChange={setEntityType}>
            <SelectTrigger>
              <SelectValue placeholder="Select entity type" />
            </SelectTrigger>
            <SelectContent>
              {ENTITY_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors
            ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
            ${file ? 'bg-muted/50' : ''}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileInput}
          />

          {file ? (
            <div className="flex items-center justify-center gap-2 text-primary">
              <FileText className="h-8 w-8" />
              <div className="text-left">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(file.size / 1024).toFixed(2)} KB
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
              <p className="font-medium">Drag and drop your CSV file here</p>
              <p className="text-sm text-muted-foreground">or click to browse</p>
            </div>
          )}
        </div>

        {uploading && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} />
          </div>
        )}

        {previewData && previewData.length > 0 && (
          <div className="space-y-2">
            <Label>Preview (first 5 rows)</Label>
            <div className="rounded-md border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    {Object.keys(previewData[0]).map((key) => (
                      <th key={key} className="px-4 py-2 text-left font-medium">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewData.map((row, idx) => (
                    <tr key={idx} className="border-t">
                      {Object.values(row).map((value: any, cellIdx) => (
                        <td key={cellIdx} className="px-4 py-2">
                          {String(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {uploadResult && (
          <Alert variant={uploadResult.success ? 'default' : 'destructive'}>
            {uploadResult.success ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <AlertDescription>{uploadResult.message}</AlertDescription>
          </Alert>
        )}

        <Button
          className="w-full"
          onClick={handleUpload}
          disabled={!file || !entityType || uploading}
        >
          {uploading ? 'Importing...' : 'Import Data'}
        </Button>
      </CardContent>
    </Card>
  );
}
