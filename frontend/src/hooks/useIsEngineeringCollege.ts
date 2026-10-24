import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

/**
 * Engineering colleges keep faculty department-wise; every other institution type does not.
 * Returns null until the institution type has been loaded.
 */
export const useIsEngineeringCollege = (): boolean | null => {
  const { user } = useAuth();
  const [isEngineering, setIsEngineering] = useState<boolean | null>(null);

  useEffect(() => {
    if (!user?.institution_id) {
      setIsEngineering(false);
      return;
    }
    let active = true;
    api
      .get<{ institution_type?: string }>(`/institutions/${user.institution_id}`)
      .then((institution) => active && setIsEngineering(institution.institution_type === 'ENGINEERING_COLLEGE'))
      .catch(() => active && setIsEngineering(false));
    return () => {
      active = false;
    };
  }, [user?.institution_id]);

  return isEngineering;
};
