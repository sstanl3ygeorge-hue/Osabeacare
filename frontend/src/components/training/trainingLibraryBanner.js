export const getPendingProposedTrainingItems = (proposedItems = []) => (
  proposedItems.filter((item) => item?.status === 'proposed')
);

export const getTrainingLibraryBannerState = ({
  proposedItems = [],
  proposedItemsErrored = false,
}) => {
  if (proposedItemsErrored) {
    return {
      tone: 'error',
      title: 'Cannot assess extracted training reviews',
      body: 'Extracted training review data did not load, so awaiting-review guidance is unavailable right now.',
    };
  }

  const pendingCount = getPendingProposedTrainingItems(proposedItems).length;
  if (pendingCount > 0) {
    return {
      tone: 'instructional',
      title: 'How training evidence becomes compliant',
      body: 'Certificates are evidence only. Extracted items appear below for review, then become canonical qualifications only after admin approval. Mandatory compliance still requires verified and current training records.',
    };
  }

  return {
    tone: 'clear',
    title: 'No extracted training items awaiting review',
    body: 'Approved qualifications below are already part of the canonical training record set. New certificate extractions will appear here only when admin review is still needed.',
  };
};
