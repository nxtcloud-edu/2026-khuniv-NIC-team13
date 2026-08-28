import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

/**
 * AutocompleteList Component
 * 
 * @param {Array} results - 표시할 자동완성 결과 리스트
 * @param {function} onSelect - 항목 선택 시 호출될 핸들러
 * @param {string} className - 추가 스타일 클래스
 */
const AutocompleteList = ({
    results = [],
    onSelect,
    anchorRef,
    className = ''
}) => {
    const [position, setPosition] = useState(null);

    useEffect(() => {
        const updatePosition = () => {
            const anchor = anchorRef?.current;
            if (!anchor) return;

            const rect = anchor.getBoundingClientRect();
            setPosition({
                top: rect.bottom + 8,
                left: rect.left,
                width: rect.width,
            });
        };

        updatePosition();
        window.addEventListener('resize', updatePosition);
        window.addEventListener('scroll', updatePosition, true);

        return () => {
            window.removeEventListener('resize', updatePosition);
            window.removeEventListener('scroll', updatePosition, true);
        };
    }, [anchorRef]);

    if (!results || results.length === 0 || !position) return null;

    return createPortal(
        <div
            className={`
                fixed z-[9999]
                h-[222px] bg-white
                rounded-[4px] 
                py-[12px] px-[10px]
                border border-[#B5B5B5]
                flex flex-col gap-[2px]
                overflow-y-auto
                autocomplete-scrollbar
                ${className}
            `}
            style={{
                boxShadow: '0px 0px 12px 0px #00000026',
                top: position.top,
                left: position.left,
                width: position.width,
            }}
        >
            {results.map((item, index) => (
                <div
                    key={index}
                    onMouseDown={(e) => {
                        // preventDefault를 통해 인풋에서 포커스가 바로 빠지는 것을 방지
                        e.preventDefault();
                        onSelect && onSelect(item);
                    }}
                    className="
                        w-full h-[48px] shrink-0
                        flex items-center pl-[8px]
                        cursor-pointer rounded-[4px]
                        bg-white hover:bg-[#ECF1F8]
                        transition-colors duration-200
                        text-[16px] text-[#000000] font-normal leading-[1.5]
                        font-['Pretendard']
                    "
                >
                    {item}
                </div>
            ))}

            <style dangerouslySetInnerHTML={{
                __html: `
                .autocomplete-scrollbar::-webkit-scrollbar {
                    width: 6px;
                }
                .autocomplete-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .autocomplete-scrollbar::-webkit-scrollbar-thumb {
                    background: #D1D1D1;
                    border-radius: 10px;
                }
                .autocomplete-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #B5B5B5;
                }
            `}} />
        </div>,
        document.body
    );
};

export default AutocompleteList;
