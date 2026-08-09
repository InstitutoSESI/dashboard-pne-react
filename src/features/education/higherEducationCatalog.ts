import type {
  HigherEducationBreakdownCatalogItem,
  HigherEducationIndicatorCatalogItem,
} from './higherEducationTypes.js'

export const HIGHER_EDUCATION_GROUPS = Object.freeze([
  { id: 'enrollments', title: 'Matrículas e modalidades', description: 'Volume e composição das matrículas de graduação no município.', order: 1 },
  { id: 'institutions', title: 'Instituições e polos', contextTitle: 'Presença de instituições e polos no município', description: 'Sedes de instituições e polos de educação a distância.', order: 2 },
  { id: 'access-flow', title: 'Acesso e fluxo', description: 'Vagas presenciais, ingressantes e concluintes.', order: 3 },
  { id: 'faculty', title: 'Docentes', description: 'Docentes vinculados às sedes institucionais do município.', order: 4 },
  { id: 'composition', title: 'Composição institucional', description: 'Distribuições por dependência, organização acadêmica e formação docente.', order: 5 },
] as const)

export const HIGHER_EDUCATION_INDICATOR_CATALOG: readonly HigherEducationIndicatorCatalogItem[] = Object.freeze([
  { id: 'esup-matriculas-total', title: 'Matrículas de graduação', description: 'Matrículas em cursos de graduação ofertados no município.', unit: 'matrículas', format: 'integer', universe: 'graduation', territorialReference: 'course_offer_location', group: 'enrollments', order: 1, relatedBreakdowns: ['enrollment_dependency', 'enrollment_organization'], readingDirection: 'contextual' },
  { id: 'esup-matriculas-presenciais', title: 'Matrículas presenciais', description: 'Matrículas em cursos presenciais de graduação ofertados no município.', unit: 'matrículas', format: 'integer', universe: 'presential_graduation', territorialReference: 'course_offer_location', group: 'enrollments', order: 2, relatedBreakdowns: [], readingDirection: 'contextual' },
  { id: 'esup-matriculas-ead', title: 'Matrículas a distância', description: 'Matrículas de graduação a distância vinculadas a locais de oferta no município.', unit: 'matrículas', format: 'integer', universe: 'distance_graduation', territorialReference: 'ead_offer_location', group: 'enrollments', order: 3, relatedBreakdowns: [], readingDirection: 'contextual' },
  { id: 'esup-ies-sede', title: 'Instituições com sede no município', description: 'Instituições de Educação Superior cuja sede administrativa está no município.', unit: 'instituições', format: 'integer', universe: 'institutions_offering_graduation_or_sequential', territorialReference: 'ies_administrative_headquarters', group: 'institutions', order: 1, relatedBreakdowns: ['ies_dependency', 'ies_organization'], readingDirection: 'contextual' },
  { id: 'esup-polos-ead', title: 'Polos de educação a distância', description: 'Polos com oferta de graduação a distância no município.', unit: 'polos', format: 'integer', universe: 'distance_graduation', territorialReference: 'ead_offer_location', group: 'institutions', order: 2, relatedBreakdowns: [], readingDirection: 'contextual' },
  { id: 'esup-vagas-presenciais', title: 'Vagas presenciais', description: 'Vagas em cursos presenciais de graduação ofertadas no município.', unit: 'vagas', format: 'integer', universe: 'presential_graduation', territorialReference: 'course_offer_location', group: 'access-flow', order: 1, relatedBreakdowns: [], readingDirection: 'contextual' },
  { id: 'esup-ingressantes', title: 'Ingressantes', description: 'Ingressantes em cursos de graduação ofertados no município.', unit: 'ingressantes', format: 'integer', universe: 'graduation', territorialReference: 'course_offer_location', group: 'access-flow', order: 2, relatedBreakdowns: [], readingDirection: 'contextual' },
  { id: 'esup-concluintes', title: 'Concluintes', description: 'Concluintes de cursos de graduação ofertados no município.', unit: 'concluintes', format: 'integer', universe: 'graduation', territorialReference: 'course_offer_location', group: 'access-flow', order: 3, relatedBreakdowns: [], readingDirection: 'contextual' },
  { id: 'esup-docentes', title: 'Docentes', description: 'Docentes de graduação ou cursos sequenciais vinculados a instituições com sede no município.', unit: 'docentes', format: 'integer', universe: 'faculty_in_graduation_or_sequential', territorialReference: 'faculty_institution_headquarters', group: 'faculty', order: 1, relatedBreakdowns: ['faculty_education'], readingDirection: 'contextual' },
])

export const HIGHER_EDUCATION_BREAKDOWN_CATALOG: readonly HigherEducationBreakdownCatalogItem[] = Object.freeze([
  { id: 'enrollment_dependency', title: 'Matrículas por dependência administrativa', description: 'Composição das matrículas de graduação por esfera administrativa.', group: 'composition', order: 1, shareAllowed: true },
  { id: 'enrollment_organization', title: 'Matrículas por organização acadêmica', description: 'Composição das matrículas por tipo de organização acadêmica.', group: 'composition', order: 2, shareAllowed: true },
  { id: 'ies_dependency', title: 'Instituições por dependência administrativa', description: 'Sedes institucionais por esfera administrativa.', group: 'composition', order: 3, shareAllowed: true },
  { id: 'ies_organization', title: 'Instituições por organização acadêmica', description: 'Sedes institucionais por tipo de organização acadêmica.', group: 'composition', order: 4, shareAllowed: true },
  { id: 'faculty_education', title: 'Docentes por grau de formação', description: 'Docentes vinculados às sedes por maior grau de formação.', group: 'composition', order: 5, shareAllowed: true },
])
