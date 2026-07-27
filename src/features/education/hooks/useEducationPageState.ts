import { useLayoutEffect, useState } from 'react'
import { useDetailViewNavigation } from '../../../hooks/useDetailViewNavigation'
import type { EducationNavigationState } from '../educationTypes'

export function useEducationPageState(currentNavigation: EducationNavigationState) {
  const [selectedSectionKey, setSelectedSectionKey] = useState(currentNavigation.section)
  const [selectedThemeKey, setSelectedThemeKey] = useState(currentNavigation.panoramaTheme)
  const [selectedIndicatorKey, setSelectedIndicatorKey] = useState(currentNavigation.detailKey)
  const [isDetailOpen, setIsDetailOpen] = useState(Boolean(currentNavigation.detailKey))
  const [searchQuery, setSearchQuery] = useState('')
  const detailNavigation = useDetailViewNavigation({ activeKey: selectedIndicatorKey, isOpen: isDetailOpen })

  useLayoutEffect(() => {
    setSelectedSectionKey((previousSection) => {
      if (previousSection !== currentNavigation.section) setSearchQuery('')
      return currentNavigation.section
    })
    if (currentNavigation.shouldApplyTheme) {
      setSelectedThemeKey((previousTheme) => {
        if (previousTheme !== currentNavigation.panoramaTheme) setSearchQuery('')
        return currentNavigation.panoramaTheme
      })
    }
    setSelectedIndicatorKey(currentNavigation.detailKey)
    setIsDetailOpen(Boolean(currentNavigation.detailKey))
  }, [
    currentNavigation.detailKey,
    currentNavigation.panoramaTheme,
    currentNavigation.section,
    currentNavigation.shouldApplyTheme,
  ])

  return {
    detailNavigation,
    isDetailOpen,
    searchQuery,
    selectedIndicatorKey,
    selectedSectionKey,
    selectedThemeKey,
    setIsDetailOpen,
    setSearchQuery,
    setSelectedIndicatorKey,
    setSelectedSectionKey,
    setSelectedThemeKey,
  }
}
