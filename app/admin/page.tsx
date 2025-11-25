"use client";

import { useState } from "react";
import { supabase } from "@/utils/supabase";
import { useRouter } from "next/navigation";

export default function AdminPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  // 입력 폼 상태 관리
  const [formData, setFormData] = useState({
    title: "",
    date: "",
    venue: "",
    lineup: "",
    poster_url: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // 쉼표(,)로 구분된 가수 이름을 배열로 변환 (예: "실리카겔, 혁오" -> ["실리카겔", "혁오"])
    const lineupArray = formData.lineup.split(",").map((s) => s.trim());

    const { error } = await supabase.from("concerts").insert([
      {
        title: formData.title,
        date: formData.date,
        venue: formData.venue,
        lineup: lineupArray,
        poster_url: formData.poster_url,
      },
    ]);

    if (error) {
      alert("업로드 실패: " + error.message);
    } else {
      alert("공연 정보가 등록되었습니다!");
      router.push("/"); // 등록 후 메인 페이지로 이동
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4 py-12 text-zinc-100">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8 backdrop-blur">
        <h2 className="text-center text-2xl font-bold tracking-tight">
          🎸 공연 정보 업로드
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 공연명 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-400">공연명</label>
            <input
              name="title"
              required
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="예: Midnight Live"
              onChange={handleChange}
            />
          </div>

          {/* 일시 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-400">일시 (자유형식)</label>
            <input
              name="date"
              required
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="예: 2025.12.25 (금) 19:00"
              onChange={handleChange}
            />
          </div>

          {/* 장소 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-400">장소</label>
            <input
              name="venue"
              required
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="예: 홍대 롤링홀"
              onChange={handleChange}
            />
          </div>

          {/* 라인업 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-400">
              라인업 (쉼표로 구분)
            </label>
            <input
              name="lineup"
              required
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="예: 실리카겔, 잔나비, 혁오"
              onChange={handleChange}
            />
          </div>

          {/* 포스터 URL */}
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-400">포스터 이미지 URL</label>
            <input
              name="poster_url"
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="https://..."
              onChange={handleChange}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-indigo-600 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "등록 중..." : "등록하기"}
          </button>
        </form>
      </div>
    </div>
  );
}