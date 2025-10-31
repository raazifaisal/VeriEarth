'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Home, Leaf } from 'lucide-react';
import type { CSSProperties } from 'react';

const leaves = [
  { id: 0, left: 4, delay: -1.2, duration: 10.4, size: 32 },
  { id: 1, left: 12, delay: -3.1, duration: 11.8, size: 28 },
  { id: 2, left: 20, delay: -5.6, duration: 9.6, size: 36 },
  { id: 3, left: 27, delay: -2.3, duration: 12.7, size: 30 },
  { id: 4, left: 33, delay: -4.8, duration: 8.9, size: 34 },
  { id: 5, left: 41, delay: -0.9, duration: 13.1, size: 38 },
  { id: 6, left: 48, delay: -2.7, duration: 9.8, size: 29 },
  { id: 7, left: 55, delay: -5.2, duration: 11.1, size: 42 },
  { id: 8, left: 62, delay: -1.4, duration: 12.3, size: 31 },
  { id: 9, left: 70, delay: -3.6, duration: 8.5, size: 35 },
  { id: 10, left: 77, delay: -4.4, duration: 10.9, size: 39 },
  { id: 11, left: 84, delay: -0.6, duration: 9.1, size: 33 },
  { id: 12, left: 91, delay: -2.9, duration: 12.8, size: 37 },
  { id: 13, left: 18, delay: -1.9, duration: 11.6, size: 26 },
  { id: 14, left: 44, delay: -4.1, duration: 10.2, size: 40 },
  { id: 15, left: 67, delay: -5.8, duration: 13.4, size: 29 },
] satisfies Array<{ id: number; left: number; delay: number; duration: number; size: number }>;

export default function NotFound() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-b from-amber-50 via-orange-100 to-emerald-50 dark:from-gray-900 dark:via-amber-950 dark:to-emerald-950 text-amber-900 dark:text-amber-100">
      <style jsx global>{`
        @keyframes leaf-fall {
          0% {
            transform: translate3d(var(--x), -120px, 0) rotate(0deg);
            opacity: 0;
          }
          10% {
            opacity: 0.8;
          }
          50% {
            transform: translate3d(calc(var(--x) + 40px), 50vh, 0) rotate(90deg);
          }
          100% {
            transform: translate3d(calc(var(--x) - 20px), 105vh, 0) rotate(180deg);
            opacity: 0;
          }
        }
      `}</style>

      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.7),transparent_60%)] dark:bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.08),transparent_55%)]" />
        <div className="absolute -left-20 bottom-10 h-64 w-[140%] rounded-[999px] bg-gradient-to-r from-amber-200/60 via-emerald-200/50 to-sky-200/60 blur-2xl dark:from-emerald-900/50 dark:via-amber-900/40 dark:to-sky-900/50" />
        <div className="absolute left-1/2 -translate-x-1/2 bottom-0 h-[55%] w-[60%] max-w-3xl bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.75),_rgba(255,255,255,0))] dark:bg-[radial-gradient(circle_at_top,_rgba(17,24,39,0.6),_rgba(17,24,39,0))] blur-lg" />
      </div>

      {leaves.map((leaf) => (
        <span
          key={leaf.id}
          className="absolute pointer-events-none"
          style={{
            '--x': `${leaf.left}vw`,
            animation: `leaf-fall ${leaf.duration}s linear infinite`,
            animationDelay: `${leaf.delay}s`,
          } as CSSProperties}
        >
          <Leaf
            className="text-amber-400/80 dark:text-amber-300/60 drop-shadow-sm"
            style={{
              width: leaf.size,
              height: leaf.size,
            }}
          />
        </span>
      ))}

      <div className="relative z-10 flex min-h-screen items-center justify-center px-6 py-20">
        <div className="mx-auto max-w-xl rounded-3xl border border-amber-200/70 bg-white/80 p-10 shadow-xl backdrop-blur dark:border-emerald-900/40 dark:bg-emerald-950/60">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-amber-100 text-amber-600 shadow-inner dark:bg-emerald-900/40 dark:text-amber-200">
            <Leaf className="h-8 w-8" />
          </div>
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-amber-500 dark:text-amber-300">
            404
          </p>
          <h1 className="mt-4 text-4xl font-black sm:text-5xl text-amber-900 dark:text-amber-100">
            Aw caw! Looks like you've wandered off the Caucal Path.
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-amber-700 dark:text-amber-200">
            This trail drifts into a misty river and never comes back. Let&apos;s head to solid ground and pick up the
            right route again.
          </p>
          <div className="mt-8">
            <Link href="/">
              <Button
                size="lg"
                className="group bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 text-white hover:from-amber-600 hover:to-orange-600 shadow-lg hover:shadow-amber-500/40"
              >
                <Home className="mr-2 h-5 w-5 transition-transform group-hover:-translate-y-0.5 group-hover:scale-110" />
                Back to the clearing
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

