'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Upload, FileText, CheckCircle2, XCircle, Loader2, Eye } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { useMutation } from '@tanstack/react-query';
import { ingestionApi } from '@/lib/api';
import { toast } from 'sonner';

interface EntityUploadCardProps {
  entityType: string;
  name: string;
  description: string;
  icon: any;
  acceptedSystems: string[];
  sampleFields: string;
  orgId: string;
}

export function EntityUploadCard({
  entityType,
  name,
  description,
  icon: Icon,
  acceptedSystems,
  sampleFields,
  orgId,
}: EntityUploadCardProps) {
  const [selectedSystem, setSelectedSystem] = useState<string>(acceptedSystems[0]);
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [previewData, setPreviewData] = useState<any[] | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => ingestionApi.upload(file, entityType, orgId),
    onSuccess: (data) => {
      setUploadStatus('success');
      toast.success(`${name} file uploaded successfully!`);
    },
    onError: (error: any) => {
      setUploadStatus('error');
      const errorMsg = error.response?.data?.detail || error.message || `Failed to upload ${name}`;
      toast.error(typeof errorMsg === 'string' ? errorMsg : 'Upload failed');
    },
  });

  const previewMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('No file selected');
      return ingestionApi.preview(file, entityType);
    },
    onSuccess: (data) => {
      setPreviewData(data.sample || []);
      setShowPreview(true);
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to load preview';
      toast.error(typeof errorMsg === 'string' ? errorMsg : 'Preview failed');
    },
  });

  const importMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('No file selected');
      return ingestionApi.import(file, entityType, orgId);
    },
    onSuccess: (data: any) => {
      const created = data.created || data.rows_imported || 0;
      toast.success(`Imported ${created} ${name.toLowerCase()} successfully!`);
      setFile(null);
      setUploadStatus('idle');
      setPreviewData(null);
      setShowPreview(false);
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Import failed';
      toast.error(typeof errorMsg === 'string' ? errorMsg : 'Import failed');
    },
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      setFile(selectedFile);
      setUploadStatus('idle');
      setPreviewData(null);
      setShowPreview(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
    },
    multiple: false,
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploadStatus('uploading');
    uploadMutation.mutate(file);
  };

  const handlePreview = async () => {
    previewMutation.mutate();
  };

  const handleImport = async () => {
    importMutation.mutate();
  };

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <Icon className="h-8 w-8 text-emerald-600 dark:text-emerald-500" />
          {acceptedSystems.length > 1 && (
            <Select value={selectedSystem} onValueChange={setSelectedSystem}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {acceptedSystems.map((system) => (
                  <SelectItem key={system} value={system}>
                    {system}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {acceptedSystems.length === 1 && (
            <Badge variant="outline">{acceptedSystems[0]}</Badge>
          )}
        </div>
        <CardTitle className="text-xl">{name}</CardTitle>
        <CardDescription className="text-sm">{description}</CardDescription>
      </CardHeader>

      <CardContent className="flex-1 space-y-4">
        {/* Upload Area */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950'
              : file
              ? 'border-emerald-300 bg-emerald-50/50 dark:bg-emerald-950/50'
              : 'border-muted-foreground/25 hover:border-emerald-500/50'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-2">
            {file ? (
              <>
                <FileText className="h-8 w-8 text-emerald-600" />
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </>
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium">Drop CSV file or click to browse</p>
                <p className="text-xs text-muted-foreground">CSV files only</p>
              </>
            )}
          </div>
        </div>

        {/* Sample Fields */}
        <div className="text-xs text-muted-foreground space-y-1">
          <p className="font-medium">Expected fields:</p>
          <p className="font-mono">{sampleFields}</p>
        </div>

        {/* Upload Status */}
        {uploadStatus === 'uploading' && (
          <div className="space-y-2">
            <Progress value={50} className="h-2" />
            <p className="text-xs text-center text-muted-foreground">Uploading...</p>
          </div>
        )}

        {uploadStatus === 'success' && (
          <div className="flex items-center gap-2 text-sm text-emerald-600">
            <CheckCircle2 className="h-4 w-4" />
            <span>Upload complete</span>
          </div>
        )}

        {uploadStatus === 'error' && (
          <div className="flex items-center gap-2 text-sm text-red-600">
            <XCircle className="h-4 w-4" />
            <span>Upload failed</span>
          </div>
        )}

        {/* Preview Data */}
        {showPreview && previewData && (
          <div className="border rounded-md p-3 max-h-40 overflow-auto text-xs">
            <p className="font-medium mb-2">Preview ({previewData.length} rows):</p>
            <pre className="text-muted-foreground">
              {JSON.stringify(previewData.slice(0, 3), null, 2)}
            </pre>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex gap-2">
        {uploadStatus !== 'success' ? (
          <Button
            onClick={handleUpload}
            disabled={!file || uploadStatus === 'uploading'}
            className="flex-1"
            size="sm"
          >
            {uploadStatus === 'uploading' ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload
              </>
            )}
          </Button>
        ) : (
          <>
            <Button
              onClick={handlePreview}
              disabled={previewMutation.isPending || !file}
              variant="outline"
              size="sm"
              className="flex-1"
            >
              {previewMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              Preview
            </Button>
            <Button
              onClick={handleImport}
              disabled={importMutation.isPending || !file}
              size="sm"
              className="flex-1"
            >
              {importMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                'Import'
              )}
            </Button>
          </>
        )}
      </CardFooter>
    </Card>
  );
}

