'use client';

import { apiRequest } from '@/lib/api-secure';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Leaf } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/auth-context';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [resending, setResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [email, setEmail] = useState('');
  const { refreshUser, user } = useAuth();

  // Set email from user if available
  useEffect(() => {
    if (user?.email) {
      setEmail(user.email);
    }
  }, [user?.email]);

  // Verify email when token is present
  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided');
      return;
    }

    // Reset resend success when new token is being verified
    setResendSuccess(false);

    const verifyEmail = async () => {
      try {
        const response = await apiRequest(`http://localhost:8000/auth/verify-email?token=${token}`);
        
        if (response.ok) {
          const data = await response.json().catch(() => ({}));
          setStatus('success');
          setMessage(data.msg || 'Email verified successfully! You can now sign in.');
          // Refresh user data to update verification status
          await refreshUser();
          return; // Exit early on success
        }
        
        // If not OK, check if user is already verified (maybe verification succeeded on first request)
        // This handles React double-rendering or duplicate requests
        const errorData = await response.json().catch(() => ({ detail: 'Invalid or expired verification token.' }));
        
        // Check user status to see if verification actually succeeded
        try {
          const userResponse = await apiRequest('http://localhost:8000/auth/me');
          if (userResponse.ok) {
            const userData = await userResponse.json();
            if (userData.is_verified) {
              // User is verified, treat as success (idempotent)
              setStatus('success');
              setMessage('Email already verified. You can sign in now.');
              await refreshUser();
              return;
            }
          }
        } catch (checkError) {
          // Ignore errors, continue with error state
        }
        
        setStatus('error');
        setMessage(errorData.detail || 'Invalid or expired verification token.');
      } catch (error) {
        // On network error, check if user is verified
        try {
          const userResponse = await apiRequest('http://localhost:8000/auth/me');
          if (userResponse.ok) {
            const userData = await userResponse.json();
            if (userData.is_verified) {
              setStatus('success');
              setMessage('Email verified successfully! You can now sign in.');
              await refreshUser();
              return;
            }
          }
        } catch (checkError) {
          // Ignore
        }
        
        setStatus('error');
        setMessage('Failed to verify email. Please try again.');
      }
    };

    verifyEmail();
  }, [token, refreshUser]);

  const handleResendVerification = async () => {
    const emailToUse = email.trim() || user?.email;
    
    if (!emailToUse) {
      setMessage('Please enter your email address.');
      return;
    }

    setResending(true);
    try {
      const response = await apiRequest('http://localhost:8000/auth/resend-verification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: emailToUse }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(data.msg || 'Verification email sent. Please check your inbox.');
        setResendSuccess(true);
        // Don't change status to 'success' - keep as 'error' so user knows they still need to verify
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to resend verification email' }));
        setMessage(errorData.detail || 'Failed to resend verification email.');
        setResendSuccess(false);
      }
    } catch (error) {
      setMessage('Failed to resend verification email. Please try again.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 via-te Brave-50 to-cyan-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate PAS900 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="shadow-lg border-2">
          <CardHeader className="text-center">
            <Link href="/" className="flex items-center justify-center gap-3 mb-4">
              <Leaf className="h-8 w-8 text-emerald-600 dark:text-emerald-500" />
              <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                  VeriEarth
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Email Verification
                </p>
              </div>
            </Link>
          </CardHeader>
          <CardContent className="text-center space-y-6">
            {status === 'loading' && (
              <>
                <Loader2 className="h-16 w-16 mx-auto text-emerald-600 animate-spin" />
                <CardTitle>Verifying your email...</CardTitle>
                <CardDescription>Please wait while we verify your email address.</CardDescription>
              </>
            )}
            
            {status === 'success' && (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring" }}
                >
                  <CheckCircle className="h-16 w-16 mx-auto text-emerald-600" />
                </motion.div>
                <CardTitle className="text-emerald-600">Verification Successful!</CardTitle>
                <CardDescription>{message}</CardDescription>
                <Link href="/signin">
                  <Button className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white">
                    Sign In Now
                  </Button>
                </Link>
              </>
            )}
            
            {status === 'error' && (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring" }}
                >
                  <XCircle className="h-16 w-16 mx-auto text-red-600" />
                </motion.div>
                <CardTitle className={resendSuccess ? "text-emerald-600" : "text-red-600"}>
                  {resendSuccess ? "Verification Email Sent!" : "Verification Failed"}
                </CardTitle>
                <CardDescription>{message}</CardDescription>
                {!resendSuccess && (
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="resend-email">Email Address</Label>
                      <Input
                        id="resend-email"
                        type="email"
                        placeholder="Enter your email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={resending}
                      />
                    </div>
                    <Button
                      variant="default"
                      className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white"
                      onClick={handleResendVerification}
                      disabled={resending || !email.trim()}
                    >
                      {resending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        'Resend Verification Email'
                      )}
                    </Button>
                  </div>
                )}
                {resendSuccess && (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Click the link in your email to verify your account.
                    </p>
                  </div>
                )}
                <div className="flex gap-2">
                  <Link href="/signin" className="flex-1">
                    <Button variant="outline" className="w-full">
                      Go to Sign In
                    </Button>
                  </Link>
                  <Link href="/signup" className="flex-1">
                    <Button variant="ghost" className="w-full">
                      Sign Up Again
                    </Button>
                  </Link>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}

