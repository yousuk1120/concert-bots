"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/utils/supabase";
import {
  format,
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
} from "date-fns";
import { ChevronLeft, ChevronRight, MapPin, Calendar as CalendarIcon, Clock } from "lucide-react";

// 데이터 타입
type Concert = {
  id: number;
  title: string;
  date: string; // "2025.11.30 (일) 19:00"
  venue: string;
  lineup: string[];
  poster_url: string;
};

export default function SmartCalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date()); // 달력의 기준 월
  const [selectedDate, setSelectedDate] = useState(new Date()); // 사용자가 클릭한 날짜
  const [concerts, setConcerts] = useState<Concert[]>([]);
  const [loading, setLoading] = useState(true);

  // 1. 데이터 가져오기
  useEffect(() => {
    fetchConcerts();
  }, []);

  async function fetchConcerts() {
    const { data, error } = await supabase
      .from("concerts")
      .select("*")
      .order("id", { ascending: false });

    if (!error) {
      setConcerts(data as Concert[]);
    }
    setLoading(false);
  }

  // 2. 달력 날짜 계산
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart);
  const endDate = endOfWeek(monthEnd);
  const calendarDays = eachDayOfInterval({ start: startDate, end: endDate });

  // 3. 날짜 비교 헬퍼 함수
  const getConcertsForDay = (day: Date) => {
    return concerts.filter((concert) => {
      const dateString = concert.date.split(" ")[0]; // "2025.11.30"
      return dateString === format(day, "yyyy.MM.dd");
    });
  };

  // 4. 선택된 날짜의 공연만 필터링 (하단 리스트용)
  const selectedConcerts = getConcertsForDay(selectedDate);

  const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));

  return (
    // 전체 화면을 꽉 채우고 스크롤을 막음 (앱 느낌)
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100 overflow-hidden">
      
      {/* === [상단] 달력 영역 === */}
      <div className="shrink-0 bg-zinc-900 pb-4 shadow-xl z-10 rounded-b-3xl border-b border-zinc-800">
        {/* 헤더 */}
        <header className="flex items-center justify-between px-6 py-4">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-widest">
              Concert Calendar
            </span>
            <h1 className="text-xl font-bold text-white">
              {format(currentDate, "yyyy년 M월")}
            </h1>
          </div>
          <div className="flex gap-2">
            <button onClick={prevMonth} className="rounded-full bg-zinc-800 p-2 hover:bg-zinc-700 transition">
              <ChevronLeft className="h-4 w-4 text-zinc-300" />
            </button>
            <button onClick={nextMonth} className="rounded-full bg-zinc-800 p-2 hover:bg-zinc-700 transition">
              <ChevronRight className="h-4 w-4 text-zinc-300" />
            </button>
          </div>
        </header>

        {/* 요일 */}
        <div className="grid grid-cols-7 mb-2 text-center text-[10px] font-bold text-zinc-500 uppercase tracking-wide">
          <div className="text-red-400">Sun</div>
          <div>Mon</div>
          <div>Tue</div>
          <div>Wed</div>
          <div>Thu</div>
          <div>Fri</div>
          <div className="text-blue-400">Sat</div>
        </div>

        {/* 날짜 그리드 */}
        <div className="grid grid-cols-7 px-2">
          {calendarDays.map((day) => {
            const dayConcerts = getConcertsForDay(day);
            const isSelected = isSameDay(day, selectedDate);
            const isCurrentMonth = isSameMonth(day, monthStart);
            const hasEvent = dayConcerts.length > 0;

            return (
              <div key={day.toString()} className="flex flex-col items-center justify-center py-1">
                <button
                  onClick={() => {
                    setSelectedDate(day);
                    // 다른 달의 날짜를 누르면 달력도 그 달로 이동
                    if (!isCurrentMonth) setCurrentDate(day);
                  }}
                  className={`relative flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition-all duration-200 
                    ${!isCurrentMonth ? "text-zinc-600" : "text-zinc-300"}
                    ${isSelected ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/50 scale-110" : "hover:bg-zinc-800"}
                  `}
                >
                  {format(day, "d")}
                  
                  {/* 이벤트가 있는 날 표시 (점) */}
                  {hasEvent && !isSelected && (
                    <span className="absolute bottom-1 h-1 w-1 rounded-full bg-indigo-500"></span>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* === [하단] 리스트 영역 (스크롤 가능) === */}
      <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
        <div className="px-6 py-4 pb-2">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="text-indigo-500">{format(selectedDate, "d일")}</span>의 일정
            <span className="ml-auto text-xs font-normal text-zinc-500 bg-zinc-900 px-2 py-1 rounded-full border border-zinc-800">
              {selectedConcerts.length}개의 공연
            </span>
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-20">
          {selectedConcerts.length > 0 ? (
            <div className="space-y-4">
              {selectedConcerts.map((concert) => (
                <div
                  key={concert.id}
                  className="flex gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-3 shadow-sm backdrop-blur-sm transition active:scale-[0.98]"
                >
                  {/* 왼쪽: 포스터 썸네일 */}
                  <div className="h-24 w-20 shrink-0 overflow-hidden rounded-xl bg-zinc-800">
                    <img
                      src={concert.poster_url}
                      alt={concert.title}
                      className="h-full w-full object-cover"
                    />
                  </div>

                  {/* 오른쪽: 정보 */}
                  <div className="flex flex-1 flex-col justify-center">
                    <div className="mb-1 text-xs font-bold uppercase text-indigo-400">Indie Live</div>
                    <h3 className="mb-1 text-base font-bold text-zinc-100 leading-tight line-clamp-2">
                      {concert.title}
                    </h3>
                    
                    <div className="flex flex-col gap-1 text-xs text-zinc-400 mt-1">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3 w-3" />
                        <span>{concert.date.split('(')[1]?.replace(')', '') || concert.date}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <MapPin className="h-3 w-3" />
                        <span>{concert.venue}</span>
                      </div>
                    </div>

                    {/* 라인업 태그 */}
                    <div className="mt-3 flex flex-wrap gap-1">
                      {concert.lineup.slice(0, 3).map((artist) => (
                        <span key={artist} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                          {artist}
                        </span>
                      ))}
                      {concert.lineup.length > 3 && (
                        <span className="text-[10px] px-1.5 py-0.5 text-zinc-500">
                          +{concert.lineup.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // 일정이 없을 때
            <div className="flex h-full flex-col items-center justify-center text-zinc-500 opacity-60">
              <CalendarIcon className="mb-2 h-10 w-10 stroke-1" />
              <p className="text-sm">등록된 공연이 없습니다.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}