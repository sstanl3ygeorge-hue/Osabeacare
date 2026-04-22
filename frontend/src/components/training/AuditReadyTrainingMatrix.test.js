import {
  getPendingProposedTrainingItems,
  getTrainingLibraryBannerState,
} from './trainingLibraryBanner';

describe('AuditReadyTrainingMatrix training library banner', () => {
  test('shows instructional banner when extracted items are awaiting review', () => {
    const proposedItems = [
      { id: 'pti_1', status: 'proposed', raw_course_title: 'Manual Handling' },
      { id: 'pti_2', status: 'approved', raw_course_title: 'Fire Safety' },
    ];

    expect(getPendingProposedTrainingItems(proposedItems)).toHaveLength(1);
    expect(getTrainingLibraryBannerState({ proposedItems })).toEqual({
      tone: 'instructional',
      title: 'How training evidence becomes compliant',
      body: 'Certificates are evidence only. Extracted items appear below for review, then become canonical qualifications only after admin approval. Mandatory compliance still requires verified and current training records.',
    });
  });

  test('shows neutral banner when no extracted items are awaiting review', () => {
    const proposedItems = [
      { id: 'pti_2', status: 'approved', raw_course_title: 'Fire Safety' },
    ];

    expect(getPendingProposedTrainingItems(proposedItems)).toHaveLength(0);
    expect(getTrainingLibraryBannerState({ proposedItems })).toEqual({
      tone: 'clear',
      title: 'No extracted training items awaiting review',
      body: 'Approved qualifications below are already part of the canonical training record set. New certificate extractions will appear here only when admin review is still needed.',
    });
  });
});
